"""
Pilot Dashboard Tab

Monitor and run pilot testing for department namespaces.
Provides UAT testing, metrics visualization, and sign-off tracking.
"""

import streamlit as st
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Import pilot components
try:
    from pilot.hr_pilot_runner import HRPilotRunner, PilotReport, UAT_QUERIES
    from pilot.hr_sample_documents import HR_SAMPLE_DOCUMENTS
    PILOT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Pilot components not available: {e}")
    PILOT_AVAILABLE = False


def render_pilot_dashboard(user, permissions, auth_middleware, **kwargs):
    """
    Pilot Testing Dashboard
    """
    
    # Extract user info
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        user_role = user.get('role', 'viewer')
    else:
        username = getattr(user, 'username', 'Unknown')
        user_role = getattr(user, 'role', 'viewer')
        if hasattr(user_role, 'value'):
            user_role = user_role.value
    
    # Log access
    if auth_middleware:
        auth_middleware.log_user_action("ACCESS_PILOT_DASHBOARD")
    
    # Header
    st.header("🧪 Pilot Testing Dashboard")
    st.caption(f"Department Namespace Pilot Testing | User: {username}")
    
    if not PILOT_AVAILABLE:
        st.error("❌ Pilot components not available")
        st.info("Ensure the `pilot/` directory is properly configured")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚀 Run Pilot",
        "📊 Results",
        "📋 Test Cases",
        "📁 Sample Docs"
    ])
    
    # ==================== RUN PILOT ====================
    with tab1:
        render_run_pilot_section(username)
    
    # ==================== RESULTS ====================
    with tab2:
        render_results_section()
    
    # ==================== TEST CASES ====================
    with tab3:
        render_test_cases_section()
    
    # ==================== SAMPLE DOCS ====================
    with tab4:
        render_sample_docs_section()


def render_run_pilot_section(username: str):
    """Render pilot execution controls"""
    
    st.subheader("🚀 Run HR Pilot")
    
    # Current status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Pilot Configuration**")
        st.info(f"""
        - **Department**: HR (Human Resources)
        - **Namespace**: `vaultmind-huron-hr-general`
        - **Documents**: {len(HR_SAMPLE_DOCUMENTS)} sample documents
        - **Test Queries**: {len(UAT_QUERIES)} UAT queries
        """)
    
    with col2:
        st.markdown("**Target Metrics**")
        st.info("""
        - **Intent Accuracy**: ≥ 90%
        - **Faithfulness Score**: ≥ 0.85
        - **P95 Latency**: < 2000ms
        """)
    
    # Run controls
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        run_full = st.button("🚀 Run Full Pilot", type="primary", help="Ingest docs + run queries")
    
    with col2:
        run_queries_only = st.button("🔍 Run Queries Only", help="Skip ingestion, run queries")
    
    with col3:
        if st.button("🔄 Reset"):
            st.session_state.pop("pilot_running", None)
            st.session_state.pop("pilot_report", None)
            st.rerun()
    
    # Execute pilot
    if run_full:
        st.session_state["pilot_running"] = True
        
        with st.spinner("Running HR Pilot... This may take a few minutes"):
            try:
                runner = HRPilotRunner()
                report = asyncio.run(runner.run_full_pilot())
                
                st.session_state["pilot_report"] = report
                st.session_state["pilot_running"] = False
                
                # Save report
                save_report(report)
                
                st.success("✅ Pilot completed!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Pilot failed: {e}")
                st.session_state["pilot_running"] = False
    
    elif run_queries_only:
        st.session_state["pilot_running"] = True
        
        with st.spinner("Running UAT queries..."):
            try:
                runner = HRPilotRunner()
                query_results = asyncio.run(runner.run_uat_queries())
                
                # Create partial report
                report = PilotReport(
                    run_id=f"queries-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    started_at=datetime.utcnow().isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    query_results=query_results,
                    total_queries=len(query_results),
                    successful_queries=sum(1 for r in query_results if r.success),
                )
                
                st.session_state["pilot_report"] = report
                st.session_state["pilot_running"] = False
                
                st.success("✅ Queries completed!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Query run failed: {e}")
                st.session_state["pilot_running"] = False
    
    # Display current report
    if "pilot_report" in st.session_state:
        report = st.session_state["pilot_report"]
        
        st.markdown("---")
        st.subheader("📊 Latest Results")
        
        # Status badge
        if report.passed:
            st.success("## ✅ PILOT PASSED")
        else:
            st.error("## ❌ PILOT FAILED")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric(
            "Intent Accuracy",
            f"{report.intent_accuracy:.0%}",
            delta="Pass" if report.intent_accuracy >= 0.9 else "Fail",
            delta_color="normal" if report.intent_accuracy >= 0.9 else "inverse"
        )
        
        col2.metric(
            "Faithfulness",
            f"{report.avg_faithfulness:.2f}",
            delta="Pass" if report.avg_faithfulness >= 0.85 else "Fail",
            delta_color="normal" if report.avg_faithfulness >= 0.85 else "inverse"
        )
        
        col3.metric(
            "P95 Latency",
            f"{report.p95_latency_ms}ms",
            delta="Pass" if report.p95_latency_ms < 2000 else "Fail",
            delta_color="normal" if report.p95_latency_ms < 2000 else "inverse"
        )
        
        col4.metric(
            "Queries",
            f"{report.successful_queries}/{report.total_queries}",
        )
        
        # Errors
        if report.errors:
            st.warning("### Errors")
            for error in report.errors:
                st.error(error)


def render_results_section():
    """Render historical results and reports"""
    
    st.subheader("📊 Pilot Results History")
    
    # Load saved reports
    reports_dir = Path("pilot/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_files = sorted(reports_dir.glob("*.json"), reverse=True)
    
    if not report_files:
        st.info("No pilot reports found. Run a pilot to generate results.")
        return
    
    # Report selector
    report_names = [f.stem for f in report_files]
    selected_report = st.selectbox(
        "Select Report",
        options=report_names,
        index=0
    )
    
    if selected_report:
        report_path = reports_dir / f"{selected_report}.json"
        
        with open(report_path) as f:
            report_data = json.load(f)
        
        # Display report
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Report Info**")
            st.write(f"- **Run ID**: {report_data.get('run_id')}")
            st.write(f"- **Started**: {report_data.get('started_at', '')[:19]}")
            st.write(f"- **Completed**: {report_data.get('completed_at', '')[:19]}")
        
        with col2:
            st.markdown("**Ingestion Stats**")
            st.write(f"- **Documents**: {report_data.get('documents_ingested', 0)}")
            st.write(f"- **Chunks**: {report_data.get('total_chunks', 0)}")
            st.write(f"- **Time**: {report_data.get('ingestion_time_ms', 0)}ms")
        
        # Metrics summary
        st.markdown("---")
        st.markdown("### Metrics")
        
        metrics_df = [
            {
                "Metric": "Intent Accuracy",
                "Result": f"{report_data.get('intent_accuracy', 0):.1%}",
                "Target": "≥ 90%",
                "Status": "✅" if report_data.get('intent_accuracy', 0) >= 0.9 else "❌"
            },
            {
                "Metric": "Avg Faithfulness",
                "Result": f"{report_data.get('avg_faithfulness', 0):.2f}",
                "Target": "≥ 0.85",
                "Status": "✅" if report_data.get('avg_faithfulness', 0) >= 0.85 else "❌"
            },
            {
                "Metric": "P95 Latency",
                "Result": f"{report_data.get('p95_latency_ms', 0)}ms",
                "Target": "< 2000ms",
                "Status": "✅" if report_data.get('p95_latency_ms', 0) < 2000 else "❌"
            },
            {
                "Metric": "Query Success Rate",
                "Result": f"{report_data.get('successful_queries', 0)}/{report_data.get('total_queries', 0)}",
                "Target": "100%",
                "Status": "✅" if report_data.get('successful_queries', 0) == report_data.get('total_queries', 0) else "⚠️"
            },
        ]
        
        st.table(metrics_df)
        
        # Raw JSON
        with st.expander("📄 Raw Report JSON"):
            st.json(report_data)


def render_test_cases_section():
    """Render UAT test case details"""
    
    st.subheader("📋 UAT Test Cases")
    
    st.info(f"**{len(UAT_QUERIES)} test queries** covering factual, procedural, analytical, and exploratory intents")
    
    # Group by intent
    intents = {}
    for tc in UAT_QUERIES:
        intent = tc["intent"]
        if intent not in intents:
            intents[intent] = []
        intents[intent].append(tc)
    
    # Display by intent
    for intent, queries in intents.items():
        with st.expander(f"**{intent.title()}** ({len(queries)} queries)", expanded=False):
            for i, tc in enumerate(queries, 1):
                st.markdown(f"**{i}. {tc['query']}**")
                st.caption(f"Expected: {', '.join(tc['expected_answer_contains'])}")
                st.caption(f"Source: `{tc['source_document']}`")
                st.markdown("---")


def render_sample_docs_section():
    """Render sample HR documents"""
    
    st.subheader("📁 Sample HR Documents")
    
    st.info(f"**{len(HR_SAMPLE_DOCUMENTS)} sample documents** for pilot testing")
    
    # Document selector
    doc_names = {data["title"]: key for key, data in HR_SAMPLE_DOCUMENTS.items()}
    selected_title = st.selectbox(
        "Select Document",
        options=list(doc_names.keys())
    )
    
    if selected_title:
        doc_key = doc_names[selected_title]
        doc_data = HR_SAMPLE_DOCUMENTS[doc_key]
        
        # Document info
        col1, col2, col3 = st.columns(3)
        col1.write(f"**Key**: `{doc_key}`")
        col2.write(f"**Type**: {doc_data.get('type', 'hr')}")
        col3.write(f"**Sensitivity**: {doc_data.get('sensitivity', 'internal')}")
        
        # Content preview
        st.markdown("---")
        content = doc_data["content"]
        
        # Word/char count
        word_count = len(content.split())
        char_count = len(content)
        st.caption(f"📊 {word_count:,} words | {char_count:,} characters")
        
        # Show content
        with st.expander("📄 Document Content", expanded=True):
            st.markdown(content)


def save_report(report: PilotReport):
    """Save pilot report to file"""
    reports_dir = Path("pilot/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / f"{report.run_id}.json"
    
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    
    logger.info(f"Saved report to {report_path}")


# Alias
render_pilot_testing = render_pilot_dashboard
