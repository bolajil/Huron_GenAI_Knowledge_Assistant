"""
LangSmith Tracing Integration for VaultMind RAG Pipeline

Provides observability and debugging capabilities for the 7-stage RAG pipeline:
- Stage 1: Intent Classification
- Stage 2: Namespace-Locked Retrieval
- Stage 3: Hybrid Search
- Stage 4: Advanced Reranking
- Stage 5: Context Assembly
- Stage 6: LLM Generation
- Stage 7: Faithfulness Validation
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

# LangSmith imports with fallback
try:
    from langsmith import Client, traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    logger.warning("LangSmith not available. Install with: pip install langsmith")
    
    # Create dummy decorators
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class Client:
        def __init__(self, *args, **kwargs):
            pass

# Check if LangSmith is configured
LANGSMITH_ENABLED = os.getenv("LANGSMITH_TRACING_V2", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "vaultmind-rag-pipeline")


class LangSmithTracer:
    """LangSmith tracing wrapper for the RAG pipeline"""
    
    def __init__(self, project_name: str = None):
        self.project_name = project_name or LANGSMITH_PROJECT
        self.enabled = LANGSMITH_AVAILABLE and LANGSMITH_ENABLED and LANGSMITH_API_KEY
        self.client = None
        
        if self.enabled:
            try:
                self.client = Client(api_key=LANGSMITH_API_KEY)
                logger.info(f"LangSmith tracing enabled for project: {self.project_name}")
            except Exception as e:
                logger.error(f"Failed to initialize LangSmith client: {e}")
                self.enabled = False
        else:
            if not LANGSMITH_AVAILABLE:
                logger.info("LangSmith package not installed")
            elif not LANGSMITH_ENABLED:
                logger.info("LangSmith tracing not enabled (set LANGSMITH_TRACING_V2=true)")
            elif not LANGSMITH_API_KEY:
                logger.info("LangSmith API key not set (set LANGSMITH_API_KEY)")
    
    def trace_stage(self, stage_name: str, stage_number: int):
        """Decorator for tracing a pipeline stage"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = datetime.now()
                metadata = {
                    "stage_name": stage_name,
                    "stage_number": stage_number,
                    "timestamp": start_time.isoformat()
                }
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success
                    end_time = datetime.now()
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    self._log_stage_completion(
                        stage_name=stage_name,
                        stage_number=stage_number,
                        duration_ms=duration_ms,
                        success=True,
                        metadata=metadata
                    )
                    
                    return result
                    
                except Exception as e:
                    # Log failure
                    end_time = datetime.now()
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    self._log_stage_completion(
                        stage_name=stage_name,
                        stage_number=stage_number,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(e),
                        metadata=metadata
                    )
                    raise
            
            return wrapper
        return decorator
    
    def _log_stage_completion(
        self,
        stage_name: str,
        stage_number: int,
        duration_ms: float,
        success: bool,
        error: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log stage completion to LangSmith"""
        try:
            log_entry = {
                "stage_name": stage_name,
                "stage_number": stage_number,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
                "metadata": metadata or {}
            }
            
            if success:
                logger.info(f"✅ Stage {stage_number} ({stage_name}) completed in {duration_ms:.2f}ms")
            else:
                logger.error(f"❌ Stage {stage_number} ({stage_name}) failed after {duration_ms:.2f}ms: {error}")
                
        except Exception as e:
            logger.warning(f"Failed to log stage completion: {e}")
    
    def trace_query(
        self,
        query: str,
        dept_id: str,
        tenant_id: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Start tracing a query through the pipeline"""
        trace_context = {
            "trace_id": f"{tenant_id}_{dept_id}_{datetime.now().timestamp()}",
            "query": query,
            "dept_id": dept_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "start_time": datetime.now().isoformat(),
            "stages": []
        }
        
        logger.info(f"🔍 Starting trace: {trace_context['trace_id']}")
        return trace_context
    
    def add_stage_to_trace(
        self,
        trace_context: Dict[str, Any],
        stage_name: str,
        stage_number: int,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        duration_ms: float
    ):
        """Add a completed stage to the trace"""
        stage_entry = {
            "stage_name": stage_name,
            "stage_number": stage_number,
            "inputs": inputs,
            "outputs": self._sanitize_outputs(outputs),
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        trace_context["stages"].append(stage_entry)
    
    def _sanitize_outputs(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize outputs for logging (remove large content)"""
        sanitized = {}
        for key, value in outputs.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:500] + f"... [truncated, {len(value)} chars total]"
            elif isinstance(value, list) and len(value) > 10:
                sanitized[key] = f"[{len(value)} items]"
            else:
                sanitized[key] = value
        return sanitized
    
    def complete_trace(
        self,
        trace_context: Dict[str, Any],
        final_result: Dict[str, Any],
        faithfulness_score: float = None
    ):
        """Complete the trace with final results"""
        trace_context["end_time"] = datetime.now().isoformat()
        trace_context["final_result"] = self._sanitize_outputs(final_result)
        trace_context["faithfulness_score"] = faithfulness_score
        
        # Calculate total duration
        start = datetime.fromisoformat(trace_context["start_time"])
        end = datetime.fromisoformat(trace_context["end_time"])
        total_duration_ms = (end - start).total_seconds() * 1000
        trace_context["total_duration_ms"] = total_duration_ms
        
        logger.info(f"✅ Trace completed: {trace_context['trace_id']} in {total_duration_ms:.2f}ms")
        
        # Log to LangSmith if available
        if self.enabled and self.client:
            self._send_trace_to_langsmith(trace_context)
        
        return trace_context
    
    def _send_trace_to_langsmith(self, trace_context: Dict[str, Any]):
        """Send trace data to LangSmith"""
        try:
            # This would use the LangSmith SDK to create a run
            # For now, we log it
            logger.debug(f"Would send trace to LangSmith: {trace_context['trace_id']}")
        except Exception as e:
            logger.warning(f"Failed to send trace to LangSmith: {e}")


# Global tracer instance
_global_tracer = None

def get_langsmith_tracer() -> LangSmithTracer:
    """Get or create the global LangSmith tracer"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = LangSmithTracer()
    return _global_tracer


# Convenience decorators for each pipeline stage
def trace_intent_classification(func):
    """Decorator for Stage 1: Intent Classification"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("intent_classification", 1)(func)

def trace_namespace_retrieval(func):
    """Decorator for Stage 2: Namespace-Locked Retrieval"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("namespace_retrieval", 2)(func)

def trace_hybrid_search(func):
    """Decorator for Stage 3: Hybrid Search"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("hybrid_search", 3)(func)

def trace_reranking(func):
    """Decorator for Stage 4: Advanced Reranking"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("advanced_reranking", 4)(func)

def trace_context_assembly(func):
    """Decorator for Stage 5: Context Assembly"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("context_assembly", 5)(func)

def trace_llm_generation(func):
    """Decorator for Stage 6: LLM Generation"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("llm_generation", 6)(func)

def trace_faithfulness_validation(func):
    """Decorator for Stage 7: Faithfulness Validation"""
    tracer = get_langsmith_tracer()
    return tracer.trace_stage("faithfulness_validation", 7)(func)


def setup_langsmith_env():
    """Helper to set up LangSmith environment variables"""
    env_template = """
# LangSmith Configuration
# Add these to your .env file

LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=your_api_key_here
LANGSMITH_PROJECT=vaultmind-rag-pipeline
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
"""
    return env_template
