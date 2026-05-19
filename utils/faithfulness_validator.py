"""
Ragas Faithfulness Validation for VaultMind RAG Pipeline

Stage 7 of the 7-stage RAG pipeline:
Validates that LLM-generated responses are grounded in the retrieved context.

Metrics:
- Faithfulness: Is the answer supported by the context?
- Answer Relevancy: Does the answer address the question?
- Context Precision: Are the retrieved contexts relevant?
- Context Recall: Do contexts cover the answer requirements?
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Ragas imports with fallback
RAGAS_AVAILABLE = False
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )
    from ragas.llms import LangchainLLMWrapper
    from datasets import Dataset
    RAGAS_AVAILABLE = True
    logger.info("Ragas faithfulness validation available")
except ImportError as e:
    logger.warning(f"Ragas not available: {e}. Install with: pip install ragas datasets")


@dataclass
class FaithfulnessResult:
    """Result of faithfulness validation"""
    faithfulness_score: float
    answer_relevancy_score: float
    context_precision_score: float
    context_recall_score: float
    overall_score: float
    is_faithful: bool
    confidence_level: str  # high, medium, low
    issues: List[str]
    suggestions: List[str]


class FaithfulnessValidator:
    """
    Validates LLM responses against retrieved context using Ragas metrics.
    
    Ensures responses are:
    1. Grounded in the provided context (faithfulness)
    2. Relevant to the user's question (answer relevancy)
    3. Based on precise context retrieval (context precision)
    4. Covering all necessary information (context recall)
    """
    
    def __init__(
        self,
        faithfulness_threshold: float = 0.7,
        relevancy_threshold: float = 0.6,
        use_llm_evaluation: bool = True
    ):
        self.faithfulness_threshold = faithfulness_threshold
        self.relevancy_threshold = relevancy_threshold
        self.use_llm_evaluation = use_llm_evaluation
        self.llm = None
        
        if RAGAS_AVAILABLE and use_llm_evaluation:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM for evaluation"""
        try:
            from langchain_openai import ChatOpenAI
            
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                base_llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=0,
                    api_key=openai_key
                )
                self.llm = LangchainLLMWrapper(base_llm)
                logger.info("Ragas LLM evaluator initialized")
            else:
                logger.warning("OpenAI API key not set for Ragas evaluation")
        except Exception as e:
            logger.warning(f"Failed to initialize Ragas LLM: {e}")
    
    def validate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: str = None
    ) -> FaithfulnessResult:
        """
        Validate the faithfulness of an answer to the retrieved contexts.
        
        Args:
            question: The user's original question
            answer: The LLM-generated answer
            contexts: List of retrieved context strings
            ground_truth: Optional ground truth answer for recall calculation
        
        Returns:
            FaithfulnessResult with scores and analysis
        """
        if not RAGAS_AVAILABLE:
            return self._fallback_validation(question, answer, contexts)
        
        try:
            # Prepare data for Ragas
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            dataset = Dataset.from_dict(data)
            
            # Select metrics based on available data
            metrics = [faithfulness, answer_relevancy, context_precision]
            if ground_truth:
                metrics.append(context_recall)
            
            # Run evaluation
            if self.llm:
                result = evaluate(dataset, metrics=metrics, llm=self.llm)
            else:
                result = evaluate(dataset, metrics=metrics)
            
            # Extract scores
            faith_score = result.get('faithfulness', 0.0)
            relevancy_score = result.get('answer_relevancy', 0.0)
            precision_score = result.get('context_precision', 0.0)
            recall_score = result.get('context_recall', 0.0) if ground_truth else 0.5
            
            # Calculate overall score
            overall = self._calculate_overall_score(
                faith_score, relevancy_score, precision_score, recall_score
            )
            
            # Determine if faithful
            is_faithful = faith_score >= self.faithfulness_threshold
            
            # Analyze issues
            issues, suggestions = self._analyze_scores(
                faith_score, relevancy_score, precision_score, recall_score
            )
            
            # Determine confidence level
            confidence = self._determine_confidence(overall)
            
            return FaithfulnessResult(
                faithfulness_score=faith_score,
                answer_relevancy_score=relevancy_score,
                context_precision_score=precision_score,
                context_recall_score=recall_score,
                overall_score=overall,
                is_faithful=is_faithful,
                confidence_level=confidence,
                issues=issues,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Ragas evaluation failed: {e}")
            return self._fallback_validation(question, answer, contexts)
    
    def _calculate_overall_score(
        self,
        faithfulness: float,
        relevancy: float,
        precision: float,
        recall: float
    ) -> float:
        """Calculate weighted overall score"""
        # Faithfulness is most important for RAG
        weights = {
            'faithfulness': 0.4,
            'relevancy': 0.3,
            'precision': 0.2,
            'recall': 0.1
        }
        
        return (
            faithfulness * weights['faithfulness'] +
            relevancy * weights['relevancy'] +
            precision * weights['precision'] +
            recall * weights['recall']
        )
    
    def _analyze_scores(
        self,
        faithfulness: float,
        relevancy: float,
        precision: float,
        recall: float
    ) -> tuple:
        """Analyze scores and generate issues/suggestions"""
        issues = []
        suggestions = []
        
        if faithfulness < self.faithfulness_threshold:
            issues.append("Answer contains claims not supported by context")
            suggestions.append("Consider rephrasing to only include information from retrieved documents")
        
        if relevancy < self.relevancy_threshold:
            issues.append("Answer may not fully address the question")
            suggestions.append("Focus more directly on what the user asked")
        
        if precision < 0.5:
            issues.append("Retrieved contexts may not be highly relevant")
            suggestions.append("Try refining search query or retrieval parameters")
        
        if recall < 0.5:
            issues.append("Answer may be missing important information")
            suggestions.append("Consider retrieving more context documents")
        
        return issues, suggestions
    
    def _determine_confidence(self, overall_score: float) -> str:
        """Determine confidence level based on overall score"""
        if overall_score >= 0.8:
            return "high"
        elif overall_score >= 0.6:
            return "medium"
        else:
            return "low"
    
    def _fallback_validation(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> FaithfulnessResult:
        """
        Fallback validation when Ragas is not available.
        Uses simple heuristics for basic faithfulness checking.
        """
        logger.info("Using fallback faithfulness validation")
        
        # Simple keyword overlap check
        answer_words = set(answer.lower().split())
        context_words = set()
        for ctx in contexts:
            context_words.update(ctx.lower().split())
        
        # Calculate overlap
        common_words = answer_words.intersection(context_words)
        
        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                    'as', 'into', 'through', 'during', 'before', 'after', 'above',
                    'below', 'between', 'under', 'again', 'further', 'then', 'once',
                    'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
                    'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just', 'also'}
        
        meaningful_common = common_words - stopwords
        meaningful_answer = answer_words - stopwords
        
        if len(meaningful_answer) > 0:
            overlap_ratio = len(meaningful_common) / len(meaningful_answer)
        else:
            overlap_ratio = 0.0
        
        # Estimate faithfulness from overlap
        faith_score = min(1.0, overlap_ratio * 1.2)  # Slightly boost
        
        # Simple relevancy check - does answer mention key question terms?
        question_words = set(question.lower().split()) - stopwords
        answer_question_overlap = len(question_words.intersection(meaningful_answer))
        relevancy_score = min(1.0, answer_question_overlap / max(1, len(question_words)))
        
        # Estimate precision from context length ratio
        total_context_len = sum(len(c) for c in contexts)
        if total_context_len > 0:
            precision_score = min(1.0, len(answer) / total_context_len * 3)
        else:
            precision_score = 0.5
        
        # Placeholder recall
        recall_score = 0.5
        
        overall = self._calculate_overall_score(
            faith_score, relevancy_score, precision_score, recall_score
        )
        
        issues, suggestions = self._analyze_scores(
            faith_score, relevancy_score, precision_score, recall_score
        )
        
        return FaithfulnessResult(
            faithfulness_score=faith_score,
            answer_relevancy_score=relevancy_score,
            context_precision_score=precision_score,
            context_recall_score=recall_score,
            overall_score=overall,
            is_faithful=faith_score >= self.faithfulness_threshold,
            confidence_level=self._determine_confidence(overall),
            issues=issues,
            suggestions=suggestions
        )
    
    def validate_batch(
        self,
        qa_pairs: List[Dict[str, Any]]
    ) -> List[FaithfulnessResult]:
        """
        Validate multiple QA pairs in batch.
        
        Args:
            qa_pairs: List of dicts with 'question', 'answer', 'contexts' keys
        
        Returns:
            List of FaithfulnessResult objects
        """
        results = []
        for pair in qa_pairs:
            result = self.validate(
                question=pair.get('question', ''),
                answer=pair.get('answer', ''),
                contexts=pair.get('contexts', []),
                ground_truth=pair.get('ground_truth')
            )
            results.append(result)
        return results
    
    def get_validation_summary(self, result: FaithfulnessResult) -> Dict[str, Any]:
        """Get a summary dict suitable for API responses"""
        return {
            'faithfulness': round(result.faithfulness_score, 3),
            'relevancy': round(result.answer_relevancy_score, 3),
            'precision': round(result.context_precision_score, 3),
            'recall': round(result.context_recall_score, 3),
            'overall': round(result.overall_score, 3),
            'is_faithful': result.is_faithful,
            'confidence': result.confidence_level,
            'issues': result.issues,
            'suggestions': result.suggestions
        }


# Global validator instance
_global_validator = None

def get_faithfulness_validator() -> FaithfulnessValidator:
    """Get or create the global faithfulness validator"""
    global _global_validator
    if _global_validator is None:
        _global_validator = FaithfulnessValidator()
    return _global_validator


def validate_response(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: str = None
) -> Dict[str, Any]:
    """
    Convenience function to validate a response.
    
    Returns a dict with validation scores and analysis.
    """
    validator = get_faithfulness_validator()
    result = validator.validate(question, answer, contexts, ground_truth)
    return validator.get_validation_summary(result)
