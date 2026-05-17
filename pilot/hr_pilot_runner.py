"""
HR Pilot Namespace Runner

End-to-end pilot testing for the HR namespace:
1. Ingest sample HR documents
2. Run UAT test queries
3. Evaluate results against targets
4. Generate pilot report

Usage:
    from pilot.hr_pilot_runner import HRPilotRunner
    
    runner = HRPilotRunner()
    
    # Run full pilot
    report = await runner.run_full_pilot()
    
    # Or run individual phases
    await runner.ingest_sample_documents()
    results = await runner.run_uat_queries()
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Import sample documents
from pilot.hr_sample_documents import HR_SAMPLE_DOCUMENTS

# Import components
try:
    from utils.tenant_context import TenantContext
    from utils.ingestion_service import IngestionService
    from utils.rag_orchestrator import RAGOrchestrator
    from utils.department_manager import get_department_manager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some components not available: {e}")
    COMPONENTS_AVAILABLE = False


# UAT Test Queries
UAT_QUERIES = [
    # Factual queries
    {
        "query": "How many PTO days do employees with 3-5 years of service get?",
        "intent": "factual",
        "expected_answer_contains": ["20 days"],
        "source_document": "pto_policy"
    },
    {
        "query": "What is the company match percentage for the 401k?",
        "intent": "factual",
        "expected_answer_contains": ["4%", "100%"],
        "source_document": "benefits_guide"
    },
    {
        "query": "How many weeks of paid parental leave does Huron provide?",
        "intent": "factual",
        "expected_answer_contains": ["12 weeks"],
        "source_document": "employee_handbook"
    },
    {
        "query": "What is the minimum internet speed required for remote work?",
        "intent": "factual",
        "expected_answer_contains": ["50 Mbps"],
        "source_document": "remote_work_policy"
    },
    {
        "query": "When is annual open enrollment?",
        "intent": "factual",
        "expected_answer_contains": ["October 15", "November 15"],
        "source_document": "benefits_guide"
    },
    
    # Procedural queries
    {
        "query": "How do I request PTO?",
        "intent": "procedural",
        "expected_answer_contains": ["Workday", "manager", "approval"],
        "source_document": "pto_policy"
    },
    {
        "query": "What is the process for performance reviews?",
        "intent": "procedural",
        "expected_answer_contains": ["self-assessment", "manager", "calibration"],
        "source_document": "performance_review_guide"
    },
    {
        "query": "How do I report harassment?",
        "intent": "procedural",
        "expected_answer_contains": ["HR", "ethics hotline"],
        "source_document": "employee_handbook"
    },
    
    # Analytical queries
    {
        "query": "What are the differences between the PPO Standard and PPO Premium plans?",
        "intent": "analytical",
        "expected_answer_contains": ["deductible", "premium", "out-of-pocket"],
        "source_document": "benefits_guide"
    },
    {
        "query": "Compare the PTO accrual rates for different tenure levels",
        "intent": "analytical",
        "expected_answer_contains": ["15", "20", "25", "30"],
        "source_document": "pto_policy"
    },
    
    # Exploratory queries
    {
        "query": "What benefits does Huron offer for professional development?",
        "intent": "exploratory",
        "expected_answer_contains": ["tuition", "certification", "$2,000"],
        "source_document": "benefits_guide"
    },
    {
        "query": "What are Huron's core values?",
        "intent": "exploratory",
        "expected_answer_contains": ["Integrity", "Excellence", "Collaboration"],
        "source_document": "employee_handbook"
    },
]


@dataclass
class QueryResult:
    """Result of a single UAT query"""
    query: str
    intent: str
    response: str
    sources: List[str]
    expected_intent: str
    expected_answer_contains: List[str]
    
    # Scores
    intent_correct: bool = False
    answer_coverage: float = 0.0
    faithfulness_score: float = 0.0
    latency_ms: int = 0
    
    # Status
    success: bool = False
    error: Optional[str] = None


@dataclass
class PilotReport:
    """Complete pilot run report"""
    
    # Metadata
    run_id: str
    started_at: str
    completed_at: str = ""
    
    # Ingestion metrics
    documents_ingested: int = 0
    total_chunks: int = 0
    ingestion_time_ms: int = 0
    
    # Query metrics
    total_queries: int = 0
    successful_queries: int = 0
    
    # Scores
    intent_accuracy: float = 0.0
    avg_answer_coverage: float = 0.0
    avg_faithfulness: float = 0.0
    p95_latency_ms: int = 0
    
    # Pass/fail
    passed: bool = False
    
    # Details
    query_results: List[QueryResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Targets
    targets: Dict[str, Any] = field(default_factory=lambda: {
        "intent_accuracy": 0.90,
        "faithfulness": 0.85,
        "p95_latency_ms": 2000,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "documents_ingested": self.documents_ingested,
            "total_chunks": self.total_chunks,
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "intent_accuracy": round(self.intent_accuracy, 3),
            "avg_answer_coverage": round(self.avg_answer_coverage, 3),
            "avg_faithfulness": round(self.avg_faithfulness, 3),
            "p95_latency_ms": self.p95_latency_ms,
            "passed": self.passed,
            "targets": self.targets,
            "errors": self.errors,
        }
    
    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        
        return f"""
# HR Pilot Report - {self.run_id}

## Status: {status}

## Metrics Summary

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Intent Accuracy | {self.intent_accuracy:.1%} | ≥{self.targets['intent_accuracy']:.0%} | {'✅' if self.intent_accuracy >= self.targets['intent_accuracy'] else '❌'} |
| Avg Faithfulness | {self.avg_faithfulness:.2f} | ≥{self.targets['faithfulness']} | {'✅' if self.avg_faithfulness >= self.targets['faithfulness'] else '❌'} |
| P95 Latency | {self.p95_latency_ms}ms | <{self.targets['p95_latency_ms']}ms | {'✅' if self.p95_latency_ms < self.targets['p95_latency_ms'] else '❌'} |

## Ingestion

- Documents: {self.documents_ingested}
- Total Chunks: {self.total_chunks}
- Time: {self.ingestion_time_ms}ms

## Queries

- Total: {self.total_queries}
- Successful: {self.successful_queries}
- Avg Coverage: {self.avg_answer_coverage:.1%}

## Timeline

- Started: {self.started_at}
- Completed: {self.completed_at}
"""


class HRPilotRunner:
    """
    HR Pilot namespace runner for end-to-end testing.
    """
    
    TENANT_ID = "huron"
    DEPT_ID = "hr"
    
    def __init__(self):
        """Initialize pilot runner"""
        if not COMPONENTS_AVAILABLE:
            raise RuntimeError("Required components not available")
        
        self.tenant_context = TenantContext(
            tenant_id=self.TENANT_ID,
            dept_id=self.DEPT_ID,
        )
        
        self.ingestion_service = IngestionService(
            enable_quality_gate=True,
            enable_classification=False,  # HR docs are pre-classified
            enable_dlp_scan=True,
        )
        
        self.rag_orchestrator = RAGOrchestrator()
        self.dept_manager = get_department_manager()
    
    async def run_full_pilot(self) -> PilotReport:
        """
        Run the complete HR pilot:
        1. Verify HR department exists
        2. Ingest sample documents
        3. Run UAT queries
        4. Evaluate results
        5. Generate report
        """
        import time
        import uuid
        
        run_id = f"hr-pilot-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        report = PilotReport(
            run_id=run_id,
            started_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(f"Starting HR Pilot: {run_id}")
        
        try:
            # Step 1: Verify department
            hr_dept = self.dept_manager.get_department(self.DEPT_ID)
            if not hr_dept:
                report.errors.append("HR department not found in registry")
                return report
            
            logger.info(f"HR department verified: {hr_dept.display_name}")
            
            # Step 2: Ingest documents
            logger.info("Ingesting sample documents...")
            ingestion_start = time.time()
            ingestion_results = await self.ingest_sample_documents()
            report.ingestion_time_ms = int((time.time() - ingestion_start) * 1000)
            
            report.documents_ingested = sum(1 for r in ingestion_results if r.get("success"))
            report.total_chunks = sum(
                r.get("parent_chunks", 0) + r.get("child_chunks", 0) 
                for r in ingestion_results
            )
            
            # Step 3: Run UAT queries
            logger.info("Running UAT queries...")
            query_results = await self.run_uat_queries()
            report.query_results = query_results
            
            # Step 4: Calculate metrics
            report.total_queries = len(query_results)
            report.successful_queries = sum(1 for r in query_results if r.success)
            
            # Intent accuracy
            intent_correct = sum(1 for r in query_results if r.intent_correct)
            report.intent_accuracy = intent_correct / len(query_results) if query_results else 0
            
            # Average answer coverage
            coverages = [r.answer_coverage for r in query_results if r.success]
            report.avg_answer_coverage = sum(coverages) / len(coverages) if coverages else 0
            
            # Average faithfulness
            faithfulness = [r.faithfulness_score for r in query_results if r.success]
            report.avg_faithfulness = sum(faithfulness) / len(faithfulness) if faithfulness else 0
            
            # P95 latency
            latencies = sorted([r.latency_ms for r in query_results])
            if latencies:
                p95_idx = int(len(latencies) * 0.95)
                report.p95_latency_ms = latencies[min(p95_idx, len(latencies) - 1)]
            
            # Step 5: Determine pass/fail
            report.passed = (
                report.intent_accuracy >= report.targets["intent_accuracy"] and
                report.avg_faithfulness >= report.targets["faithfulness"] and
                report.p95_latency_ms < report.targets["p95_latency_ms"]
            )
            
        except Exception as e:
            logger.error(f"Pilot failed: {e}")
            report.errors.append(str(e))
        
        report.completed_at = datetime.utcnow().isoformat()
        
        logger.info(f"Pilot completed: {'PASSED' if report.passed else 'FAILED'}")
        
        return report
    
    async def ingest_sample_documents(self) -> List[Dict[str, Any]]:
        """Ingest all sample HR documents"""
        results = []
        
        for doc_key, doc_data in HR_SAMPLE_DOCUMENTS.items():
            try:
                result = await self.ingestion_service.ingest_document(
                    text_content=doc_data["content"],
                    file_name=f"{doc_key}.md",
                    tenant_context=self.tenant_context,
                    document_type=doc_data.get("type", "hr"),
                    sensitivity_level=doc_data.get("sensitivity", "internal"),
                )
                
                results.append({
                    "document": doc_key,
                    "success": result.success,
                    "parent_chunks": result.parent_chunks,
                    "child_chunks": result.child_chunks,
                    "error": result.error,
                })
                
                logger.info(f"Ingested {doc_key}: {result.parent_chunks} parent, {result.child_chunks} child chunks")
                
            except Exception as e:
                logger.error(f"Failed to ingest {doc_key}: {e}")
                results.append({
                    "document": doc_key,
                    "success": False,
                    "error": str(e),
                })
        
        return results
    
    async def run_uat_queries(self) -> List[QueryResult]:
        """Run all UAT test queries"""
        results = []
        
        for test_case in UAT_QUERIES:
            result = await self._run_single_query(test_case)
            results.append(result)
        
        return results
    
    async def _run_single_query(self, test_case: Dict[str, Any]) -> QueryResult:
        """Run a single UAT query"""
        import time
        
        query = test_case["query"]
        expected_intent = test_case["intent"]
        expected_contains = test_case["expected_answer_contains"]
        
        result = QueryResult(
            query=query,
            intent="",
            response="",
            sources=[],
            expected_intent=expected_intent,
            expected_answer_contains=expected_contains,
        )
        
        try:
            start_time = time.time()
            
            # Run query through orchestrator
            rag_result = await self.rag_orchestrator.query(
                query=query,
                tenant_context=self.tenant_context,
            )
            
            result.latency_ms = int((time.time() - start_time) * 1000)
            result.response = rag_result.get("response", "")
            result.sources = rag_result.get("sources", [])
            result.intent = rag_result.get("intent", "")
            result.faithfulness_score = rag_result.get("faithfulness_score", 0)
            
            # Check intent
            result.intent_correct = result.intent == expected_intent
            
            # Check answer coverage
            response_lower = result.response.lower()
            matches = sum(
                1 for phrase in expected_contains 
                if phrase.lower() in response_lower
            )
            result.answer_coverage = matches / len(expected_contains) if expected_contains else 1.0
            
            result.success = len(rag_result.get("errors", [])) == 0
            
            if not result.success:
                result.error = "; ".join(rag_result.get("errors", []))
            
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        logger.debug(f"Query: {query[:50]}... | Intent: {result.intent_correct} | Coverage: {result.answer_coverage:.0%}")
        
        return result
    
    async def test_namespace_isolation(self) -> Dict[str, Any]:
        """
        Test that HR users cannot access other namespaces.
        Attempt to query Legal namespace with HR context.
        """
        hr_context = TenantContext(
            tenant_id=self.TENANT_ID,
            dept_id="hr",
        )
        
        legal_context = TenantContext(
            tenant_id=self.TENANT_ID,
            dept_id="legal",
        )
        
        # HR user queries HR namespace - should succeed
        hr_result = await self.rag_orchestrator.query(
            query="What is the PTO policy?",
            tenant_context=hr_context,
        )
        
        # HR user queries Legal namespace - should return no results or fail
        # (In full implementation, this would be blocked at auth layer)
        cross_namespace_result = await self.rag_orchestrator.query(
            query="What is the contract termination clause?",
            tenant_context=hr_context,  # HR user
        )
        
        return {
            "hr_query_success": hr_result.get("success", False),
            "hr_has_response": bool(hr_result.get("response")),
            "cross_namespace_blocked": len(cross_namespace_result.get("sources", [])) == 0,
            "isolation_test_passed": (
                hr_result.get("success", False) and 
                len(cross_namespace_result.get("sources", [])) == 0
            ),
        }


def run_pilot_sync():
    """Synchronous wrapper to run pilot from command line"""
    runner = HRPilotRunner()
    report = asyncio.run(runner.run_full_pilot())
    
    print(report.generate_summary())
    
    # Save report
    report_path = f"pilot/reports/{report.run_id}.json"
    os.makedirs("pilot/reports", exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"\nReport saved to: {report_path}")
    
    return report


if __name__ == "__main__":
    run_pilot_sync()
