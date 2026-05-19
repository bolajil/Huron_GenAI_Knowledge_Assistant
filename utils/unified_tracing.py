"""
Unified Tracing for VaultMind RAG Pipeline

Supports both LangSmith and Langfuse for comprehensive observability.
Automatically uses whichever platform(s) are configured.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Import both tracers
from utils.langsmith_tracing import get_langsmith_tracer, LangSmithTracer
from utils.langfuse_tracing import get_langfuse_tracer, LangfuseTracer


class UnifiedTracer:
    """Unified tracing that sends to both LangSmith and Langfuse"""
    
    def __init__(self):
        self.langsmith = get_langsmith_tracer()
        self.langfuse = get_langfuse_tracer()
        
        self.langsmith_enabled = self.langsmith.enabled
        self.langfuse_enabled = self.langfuse.enabled
        
        platforms = []
        if self.langsmith_enabled:
            platforms.append("LangSmith")
        if self.langfuse_enabled:
            platforms.append("Langfuse")
        
        if platforms:
            logger.info(f"Unified tracing enabled: {', '.join(platforms)}")
        else:
            logger.info("No tracing platforms configured")
    
    @property
    def enabled(self) -> bool:
        """Check if any tracing platform is enabled"""
        return self.langsmith_enabled or self.langfuse_enabled
    
    def start_trace(
        self,
        name: str,
        query: str,
        dept_id: str,
        tenant_id: str,
        user_id: str = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Start traces on all enabled platforms"""
        trace_context = {
            "unified_trace_id": f"{tenant_id}_{dept_id}_{datetime.now().timestamp()}",
            "query": query,
            "dept_id": dept_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "start_time": datetime.now(),
            "stages": [],
            "langsmith_context": None,
            "langfuse_trace_id": None
        }
        
        # Start LangSmith trace
        if self.langsmith_enabled:
            trace_context["langsmith_context"] = self.langsmith.trace_query(
                query, dept_id or "general", tenant_id, user_id
            )
        
        # Start Langfuse trace
        if self.langfuse_enabled:
            trace_context["langfuse_trace_id"] = self.langfuse.start_trace(
                name=name,
                query=query,
                dept_id=dept_id,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata
            )
        
        logger.info(f"🔍 Unified trace started: {trace_context['unified_trace_id']}")
        return trace_context
    
    @contextmanager
    def trace_stage(
        self,
        trace_context: Dict[str, Any],
        stage_name: str,
        stage_number: int,
        input_data: Dict[str, Any] = None
    ):
        """Context manager to trace a pipeline stage on all platforms"""
        start_time = datetime.now()
        langfuse_span_id = None
        
        # Start Langfuse span
        if self.langfuse_enabled and trace_context.get("langfuse_trace_id"):
            langfuse_span_id = self.langfuse.start_span(
                trace_context["langfuse_trace_id"],
                stage_name,
                stage_number,
                input_data
            )
        
        try:
            yield
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log success to both platforms
            stage_entry = {
                "stage_name": stage_name,
                "stage_number": stage_number,
                "duration_ms": duration_ms,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            trace_context["stages"].append(stage_entry)
            
            # End Langfuse span
            if self.langfuse_enabled and langfuse_span_id:
                self.langfuse.end_span(
                    trace_context["langfuse_trace_id"],
                    langfuse_span_id,
                    {"status": "success", "duration_ms": duration_ms}
                )
            
            # Add to LangSmith trace
            if self.langsmith_enabled and trace_context.get("langsmith_context"):
                self.langsmith.add_stage_to_trace(
                    trace_context["langsmith_context"],
                    stage_name,
                    stage_number,
                    input_data or {},
                    {"status": "success"},
                    duration_ms
                )
            
            logger.info(f"✅ Stage {stage_number} ({stage_name}) completed in {duration_ms:.2f}ms")
            
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log failure
            stage_entry = {
                "stage_name": stage_name,
                "stage_number": stage_number,
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            trace_context["stages"].append(stage_entry)
            
            # End Langfuse span with error
            if self.langfuse_enabled and langfuse_span_id:
                self.langfuse.end_span(
                    trace_context["langfuse_trace_id"],
                    langfuse_span_id,
                    {"error": str(e)},
                    level="ERROR"
                )
            
            logger.error(f"❌ Stage {stage_number} ({stage_name}) failed: {e}")
            raise
    
    def log_generation(
        self,
        trace_context: Dict[str, Any],
        name: str,
        model: str,
        prompt: str,
        completion: str,
        usage: Dict[str, int] = None
    ):
        """Log an LLM generation to all platforms"""
        if self.langfuse_enabled and trace_context.get("langfuse_trace_id"):
            self.langfuse.log_generation(
                trace_context["langfuse_trace_id"],
                name,
                model,
                prompt,
                completion,
                usage
            )
    
    def add_score(
        self,
        trace_context: Dict[str, Any],
        name: str,
        value: float,
        comment: str = None
    ):
        """Add a score (e.g., faithfulness, user feedback) to all platforms"""
        if self.langfuse_enabled and trace_context.get("langfuse_trace_id"):
            self.langfuse.score_trace(
                trace_context["langfuse_trace_id"],
                name,
                value,
                comment
            )
    
    def end_trace(
        self,
        trace_context: Dict[str, Any],
        output: Dict[str, Any] = None,
        scores: Dict[str, float] = None
    ):
        """End traces on all platforms"""
        duration_ms = (datetime.now() - trace_context["start_time"]).total_seconds() * 1000
        
        # Complete LangSmith trace
        if self.langsmith_enabled and trace_context.get("langsmith_context"):
            self.langsmith.complete_trace(
                trace_context["langsmith_context"],
                output or {},
                scores.get("faithfulness") if scores else None
            )
        
        # Complete Langfuse trace
        if self.langfuse_enabled and trace_context.get("langfuse_trace_id"):
            self.langfuse.end_trace(
                trace_context["langfuse_trace_id"],
                output,
                scores=scores
            )
        
        logger.info(f"✅ Unified trace completed: {trace_context['unified_trace_id']} in {duration_ms:.2f}ms")
    
    def flush(self):
        """Flush all pending traces"""
        if self.langfuse_enabled:
            self.langfuse.flush()


# Global unified tracer instance
_global_unified_tracer = None

def get_unified_tracer() -> UnifiedTracer:
    """Get or create the global unified tracer"""
    global _global_unified_tracer
    if _global_unified_tracer is None:
        _global_unified_tracer = UnifiedTracer()
    return _global_unified_tracer


def trace_rag_pipeline(
    query: str,
    dept_id: str = "general",
    tenant_id: str = "huron",
    user_id: str = None
):
    """Convenience function to start tracing a RAG query"""
    tracer = get_unified_tracer()
    return tracer.start_trace(
        name="RAG Query",
        query=query,
        dept_id=dept_id,
        tenant_id=tenant_id,
        user_id=user_id
    )


def setup_tracing_env():
    """Helper to set up all tracing environment variables"""
    env_template = """
# ============================================
# Observability & Tracing Configuration
# ============================================

# --- LangSmith (LangChain's platform) ---
# Sign up at https://smith.langchain.com/
LANGSMITH_TRACING_V2=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=vaultmind-rag-pipeline
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# --- Langfuse (Open-source alternative) ---
# Sign up at https://cloud.langfuse.com/ or self-host
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
"""
    return env_template
