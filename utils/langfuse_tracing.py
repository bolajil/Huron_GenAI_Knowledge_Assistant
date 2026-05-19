"""
Langfuse Tracing Integration for VaultMind RAG Pipeline

Langfuse is an open-source LLM observability platform.
https://langfuse.com

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
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Langfuse imports with fallback
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("Langfuse not available. Install with: pip install langfuse")
    
    # Create dummy decorator
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class langfuse_context:
        @staticmethod
        def update_current_trace(*args, **kwargs):
            pass
        @staticmethod
        def update_current_observation(*args, **kwargs):
            pass
        @staticmethod
        def flush():
            pass
    
    class Langfuse:
        def __init__(self, *args, **kwargs):
            pass
        def trace(self, *args, **kwargs):
            return DummyTrace()
        def flush(self):
            pass
    
    class DummyTrace:
        def span(self, *args, **kwargs):
            return DummySpan()
        def generation(self, *args, **kwargs):
            return self
        def end(self, *args, **kwargs):
            pass
        def update(self, *args, **kwargs):
            pass
    
    class DummySpan:
        def end(self, *args, **kwargs):
            pass
        def update(self, *args, **kwargs):
            pass

# Environment variables
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


class LangfuseTracer:
    """Langfuse tracing wrapper for the RAG pipeline"""
    
    def __init__(self):
        self.enabled = LANGFUSE_AVAILABLE and LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
        self.client = None
        self.active_traces = {}
        
        if self.enabled:
            try:
                self.client = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST
                )
                logger.info(f"Langfuse tracing enabled at {LANGFUSE_HOST}")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {e}")
                self.enabled = False
        else:
            if not LANGFUSE_AVAILABLE:
                logger.info("Langfuse package not installed")
            elif not LANGFUSE_ENABLED:
                logger.info("Langfuse tracing not enabled (set LANGFUSE_ENABLED=true)")
            elif not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
                logger.info("Langfuse keys not set (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)")
    
    def start_trace(
        self,
        name: str,
        query: str,
        dept_id: str,
        tenant_id: str,
        user_id: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Start a new trace for a query"""
        trace_id = f"{tenant_id}_{dept_id}_{datetime.now().timestamp()}"
        
        if not self.enabled:
            return trace_id
        
        try:
            trace = self.client.trace(
                name=name,
                id=trace_id,
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "dept_id": dept_id,
                    "tenant_id": tenant_id,
                    "query": query,
                    **(metadata or {})
                },
                input={"query": query}
            )
            
            self.active_traces[trace_id] = {
                "trace": trace,
                "spans": {},
                "start_time": datetime.now()
            }
            
            logger.info(f"🔍 Langfuse trace started: {trace_id}")
            return trace_id
            
        except Exception as e:
            logger.warning(f"Failed to start Langfuse trace: {e}")
            return trace_id
    
    def start_span(
        self,
        trace_id: str,
        span_name: str,
        stage_number: int,
        input_data: Dict[str, Any] = None
    ) -> Optional[str]:
        """Start a span within a trace"""
        if not self.enabled or trace_id not in self.active_traces:
            return None
        
        span_id = f"{span_name}_{stage_number}"
        
        try:
            trace_data = self.active_traces[trace_id]
            span = trace_data["trace"].span(
                name=span_name,
                metadata={"stage_number": stage_number},
                input=input_data
            )
            
            trace_data["spans"][span_id] = {
                "span": span,
                "start_time": datetime.now()
            }
            
            return span_id
            
        except Exception as e:
            logger.warning(f"Failed to start Langfuse span: {e}")
            return None
    
    def end_span(
        self,
        trace_id: str,
        span_id: str,
        output_data: Dict[str, Any] = None,
        level: str = "DEFAULT"
    ):
        """End a span with output data"""
        if not self.enabled or trace_id not in self.active_traces:
            return
        
        try:
            trace_data = self.active_traces[trace_id]
            if span_id in trace_data["spans"]:
                span_data = trace_data["spans"][span_id]
                duration_ms = (datetime.now() - span_data["start_time"]).total_seconds() * 1000
                
                span_data["span"].end(
                    output=output_data,
                    level=level,
                    status_message=f"Completed in {duration_ms:.2f}ms"
                )
                
                logger.debug(f"Span {span_id} ended in {duration_ms:.2f}ms")
                
        except Exception as e:
            logger.warning(f"Failed to end Langfuse span: {e}")
    
    def log_generation(
        self,
        trace_id: str,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        usage: Dict[str, int] = None
    ):
        """Log an LLM generation"""
        if not self.enabled or trace_id not in self.active_traces:
            return
        
        try:
            trace_data = self.active_traces[trace_id]
            trace_data["trace"].generation(
                name=name,
                model=model,
                input=prompt,
                output=completion,
                usage=usage
            )
            
        except Exception as e:
            logger.warning(f"Failed to log Langfuse generation: {e}")
    
    def end_trace(
        self,
        trace_id: str,
        output: Dict[str, Any] = None,
        level: str = "DEFAULT",
        scores: Dict[str, float] = None
    ):
        """End a trace with final output"""
        if not self.enabled or trace_id not in self.active_traces:
            return
        
        try:
            trace_data = self.active_traces[trace_id]
            duration_ms = (datetime.now() - trace_data["start_time"]).total_seconds() * 1000
            
            trace_data["trace"].update(
                output=output,
                level=level
            )
            
            # Add scores if provided (e.g., faithfulness, relevance)
            if scores:
                for score_name, score_value in scores.items():
                    trace_data["trace"].score(
                        name=score_name,
                        value=score_value
                    )
            
            # Flush to ensure data is sent
            self.client.flush()
            
            logger.info(f"✅ Langfuse trace completed: {trace_id} in {duration_ms:.2f}ms")
            
            # Clean up
            del self.active_traces[trace_id]
            
        except Exception as e:
            logger.warning(f"Failed to end Langfuse trace: {e}")
    
    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str = None
    ):
        """Add a score to a trace (e.g., faithfulness, user feedback)"""
        if not self.enabled or trace_id not in self.active_traces:
            return
        
        try:
            trace_data = self.active_traces[trace_id]
            trace_data["trace"].score(
                name=name,
                value=value,
                comment=comment
            )
            
        except Exception as e:
            logger.warning(f"Failed to add Langfuse score: {e}")
    
    @contextmanager
    def trace_stage(self, trace_id: str, stage_name: str, stage_number: int, input_data: Dict = None):
        """Context manager for tracing a pipeline stage"""
        span_id = self.start_span(trace_id, stage_name, stage_number, input_data)
        try:
            yield span_id
        except Exception as e:
            self.end_span(trace_id, span_id, {"error": str(e)}, level="ERROR")
            raise
        else:
            self.end_span(trace_id, span_id, {"status": "success"})
    
    def flush(self):
        """Flush all pending traces"""
        if self.enabled and self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")


# Global tracer instance
_global_langfuse_tracer = None

def get_langfuse_tracer() -> LangfuseTracer:
    """Get or create the global Langfuse tracer"""
    global _global_langfuse_tracer
    if _global_langfuse_tracer is None:
        _global_langfuse_tracer = LangfuseTracer()
    return _global_langfuse_tracer


# Convenience decorator using Langfuse's native decorator
def trace_with_langfuse(name: str = None):
    """Decorator to trace a function with Langfuse"""
    if LANGFUSE_AVAILABLE and LANGFUSE_ENABLED:
        return observe(name=name)
    else:
        def decorator(func):
            return func
        return decorator


def setup_langfuse_env():
    """Helper to set up Langfuse environment variables"""
    env_template = """
# Langfuse Configuration
# Add these to your .env file
# Sign up at https://cloud.langfuse.com to get keys

LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
"""
    return env_template
