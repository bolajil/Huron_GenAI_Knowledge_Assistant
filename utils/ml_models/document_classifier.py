"""
Document Classifier using PyTorch and Transformers
Auto-categorizes documents for better organization and retrieval
"""

import os
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# PyTorch and Transformers imports with fallback
try:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        Trainer,
        TrainingArguments,
        EarlyStoppingCallback
    )
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True

    class DocumentDataset(Dataset):
        """Custom dataset for document classification"""
        
        def __init__(self, texts, labels, tokenizer, max_length=512):
            self.texts = texts
            self.labels = labels
            self.tokenizer = tokenizer
            self.max_length = max_length
        
        def __len__(self):
            return len(self.texts)
        
        def __getitem__(self, idx):
            text = self.texts[idx]
            label = self.labels[idx]
            
            encoding = self.tokenizer(
                text,
                add_special_tokens=True,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            return {
                'input_ids': encoding['input_ids'].flatten(),
                'attention_mask': encoding['attention_mask'].flatten(),
                'labels': torch.tensor(label, dtype=torch.long)
            }
    
    

except ImportError:
    logger.warning("PyTorch/Transformers not available. Install with: pip install torch transformers")
    TORCH_AVAILABLE = False
    DocumentDataset = None


class DocumentClassifier:
    """
    Classify documents into categories using transformer models
    
    Document Categories:
    - Legal: Contracts, policies, regulations
    - Technical: Specifications, manuals, documentation
    - Financial: Reports, budgets, invoices
    - HR: Employee docs, policies, procedures
    - Operations: Processes, workflows, SOPs
    - Marketing: Campaigns, content, strategies
    - Research: Papers, studies, analysis
    - Administrative: Memos, correspondence
    - Training: Materials, guides, tutorials
    - General: Uncategorized documents
    """
    
    DOCUMENT_CATEGORIES = [
        'legal',
        'technical',
        'financial',
        'hr',
        'operations',
        'marketing',
        'research',
        'administrative',
        'training',
        'general'
    ]
    
    def __init__(self,
                 model_name: str = "microsoft/deberta-v3-base",
                 model_path: Optional[str] = None):
        """
        Initialize document classifier
        
        Args:
            model_name: Pre-trained model to use
            model_path: Path to saved fine-tuned model
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch and Transformers are required for DocumentClassifier")
        
        self.model_name = model_name
        self.model_path = model_path or "data/ml_models/document_classifier"
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.tokenizer = None
        self.model = None
        self.label_to_id = {label: idx for idx, label in enumerate(self.DOCUMENT_CATEGORIES)}
        self.id_to_label = {idx: label for label, idx in self.label_to_id.items()}
        
        # Try to load existing model
        if Path(self.model_path).exists() and Path(os.path.join(self.model_path, 'pytorch_model.bin')).exists():
            self.load_model()
        else:
            logger.info("No pre-trained model found. Will use base model.")
            self._initialize_base_model()
    
    def _initialize_base_model(self):
        """Initialize base model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=len(self.DOCUMENT_CATEGORIES),
                problem_type="single_label_classification"
            )
            self.model.to(self.device)
            logger.info(f"Initialized base model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize base model: {e}")
            raise
    
    def train(self,
              documents: List[str],
              labels: List[str],
              validation_split: float = 0.2,
              epochs: int = 3,
              batch_size: int = 8,
              learning_rate: float = 2e-5) -> Dict:
        """
        Fine-tune the model on your documents
        
        Args:
            documents: List of document texts
            labels: List of category labels
            validation_split: Fraction for validation
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            
        Returns:
            Training metrics
        """
        logger.info(f"Training document classifier on {len(documents)} documents")
        
        # Validate labels
        invalid_labels = set(labels) - set(self.DOCUMENT_CATEGORIES)
        if invalid_labels:
            raise ValueError(f"Invalid labels: {invalid_labels}")
        
        # Convert labels to IDs
        label_ids = [self.label_to_id[label] for label in labels]
        
        # Split data
        split_idx = int(len(documents) * (1 - validation_split))
        train_texts = documents[:split_idx]
        train_labels = label_ids[:split_idx]
        val_texts = documents[split_idx:]
        val_labels = label_ids[split_idx:]
        
        # Create datasets
        train_dataset = DocumentDataset(train_texts, train_labels, self.tokenizer)
        val_dataset = DocumentDataset(val_texts, val_labels, self.tokenizer)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.model_path,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            logging_dir=os.path.join(self.model_path, 'logs'),
            logging_steps=10,
            save_total_limit=2,
            fp16=torch.cuda.is_available(),
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
        )
        
        # Train
        train_result = trainer.train()
        
        # Save model
        self.save_model()
        
        logger.info("Training completed successfully")
        
        return {
            'train_loss': train_result.training_loss,
            'metrics': train_result.metrics
        }
    
    def classify_document(self, content: str, return_all_scores: bool = False) -> Dict:
        """
        Classify a single document
        
        Args:
            content: Document text
            return_all_scores: Return scores for all categories
            
        Returns:
            Classification results with category, confidence, and metadata
        """
        if self.model is None:
            raise ValueError("Model not initialized")
        
        # Tokenize
        inputs = self.tokenizer(
            content,
            add_special_tokens=True,
            max_length=512,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)[0]
        
        # Get top prediction
        top_idx = torch.argmax(probabilities).item()
        top_category = self.id_to_label[top_idx]
        confidence = probabilities[top_idx].item()
        
        result = {
            'category': top_category,
            'confidence': confidence,
            'metadata': self._extract_metadata(content, top_category)
        }
        
        if return_all_scores:
            result['all_categories'] = {
                self.id_to_label[i]: prob.item()
                for i, prob in enumerate(probabilities)
            }
        
        return result
    
    def classify_batch(self, documents: List[str]) -> List[Dict]:
        """Classify multiple documents efficiently"""
        results = []
        
        # Process in batches
        batch_size = 8
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                add_special_tokens=True,
                max_length=512,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
            
            # Process results
            for doc, probs in zip(batch, probabilities):
                top_idx = torch.argmax(probs).item()
                results.append({
                    'category': self.id_to_label[top_idx],
                    'confidence': probs[top_idx].item(),
                    'metadata': self._extract_metadata(doc, self.id_to_label[top_idx])
                })
        
        return results
    
    def _extract_metadata(self, content: str, category: str) -> Dict:
        """Extract category-specific metadata"""
        metadata = {
            'category': category,
            'word_count': len(content.split()),
            'char_count': len(content)
        }
        
        # Category-specific extraction
        if category == 'legal':
            metadata['keywords'] = self._extract_legal_keywords(content)
        elif category == 'financial':
            metadata['keywords'] = self._extract_financial_keywords(content)
        elif category == 'technical':
            metadata['keywords'] = self._extract_technical_keywords(content)
        
        return metadata
    
    def _extract_legal_keywords(self, content: str) -> List[str]:
        """Extract legal-specific keywords"""
        legal_terms = [
            'contract', 'agreement', 'clause', 'provision', 'liability',
            'warranty', 'indemnity', 'confidential', 'compliance', 'regulation'
        ]
        content_lower = content.lower()
        return [term for term in legal_terms if term in content_lower]
    
    def _extract_financial_keywords(self, content: str) -> List[str]:
        """Extract financial-specific keywords"""
        financial_terms = [
            'revenue', 'profit', 'expense', 'budget', 'forecast',
            'investment', 'roi', 'cash flow', 'balance sheet', 'income'
        ]
        content_lower = content.lower()
        return [term for term in financial_terms if term in content_lower]
    
    def _extract_technical_keywords(self, content: str) -> List[str]:
        """Extract technical-specific keywords"""
        technical_terms = [
            'specification', 'architecture', 'implementation', 'configuration',
            'deployment', 'integration', 'api', 'database', 'system', 'protocol'
        ]
        content_lower = content.lower()
        return [term for term in technical_terms if term in content_lower]
    
    def save_model(self):
        """Save model and tokenizer"""
        if self.model is None:
            raise ValueError("No model to save")
        
        # Create directory
        Path(self.model_path).mkdir(parents=True, exist_ok=True)
        
        # Save model and tokenizer
        self.model.save_pretrained(self.model_path)
        self.tokenizer.save_pretrained(self.model_path)
        
        # Save label mappings
        with open(os.path.join(self.model_path, 'label_mappings.json'), 'w') as f:
            json.dump({
                'label_to_id': self.label_to_id,
                'id_to_label': self.id_to_label
            }, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load saved model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            
            # Load label mappings
            with open(os.path.join(self.model_path, 'label_mappings.json'), 'r') as f:
                mappings = json.load(f)
                self.label_to_id = mappings['label_to_id']
                self.id_to_label = {int(k): v for k, v in mappings['id_to_label'].items()}
            
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise


# Singleton instance
_classifier_instance = None

def get_document_classifier(model_path: Optional[str] = None) -> DocumentClassifier:
    """Get or create singleton instance of DocumentClassifier"""
    global _classifier_instance
    
    if _classifier_instance is None:
        _classifier_instance = DocumentClassifier(model_path=model_path)
    
    return _classifier_instance
