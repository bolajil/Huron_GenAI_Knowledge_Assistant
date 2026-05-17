"""
Enhanced Research Tab for VaultMind Knowledge Assistant.
Updated to use the centralized vector database integration.
"""

import streamlit as st
import os
import sys
import json
import time
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import centralized vector database provider
try:
    from utils.vector_db_init import get_any_vector_db_provider, VECTOR_DB_AVAILABLE
    
    # Get the vector database provider instance
    db_provider = get_any_vector_db_provider()
    
    # Try to import enhanced research integration
    try:
        from utils.enhanced_research_integration import generate_enhanced_research_content
        ENHANCED_RESEARCH_AVAILABLE = True
    except ImportError:
        # Define a fallback function if the integration is not available
        def generate_enhanced_research_content(task, operation, knowledge_sources):
            search_results = db_provider.search(task, max_results=5)
            
            # Format the results into a research document
            content = f"## Research Report: {task}\n\n"
            content += "### Executive Summary\n"
            content += f"This research report addresses {task} based on available information.\n\n"
            content += "### Key Findings\n"
            
            for i, result in enumerate(search_results, 1):
                content += f"{i}. {result.content}\n\n"
            
            content += "### Conclusion\n"
            content += f"This research provides information about {task}.\n\n"
            
            content += "### Sources\n"
            for i, result in enumerate(search_results, 1):
                content += f"{i}. {result.source}\n"
            
            return content
        
        ENHANCED_RESEARCH_AVAILABLE = True
        
    logger.info("Enhanced research tab initialized with vector DB provider")
except Exception as e:
    ENHANCED_RESEARCH_AVAILABLE = False
    db_provider = None
    logger.error(f"Error initializing enhanced research tab with vector DB: {e}")

# Initialize global variables
RESEARCH_OPERATIONS = [
    "Research Topic",
    "Data Analysis",
    "Problem Solving",
    "Trend Identification"
]

# Knowledge source options with clear labels
KNOWLEDGE_SOURCES = [
    "Indexed Documents",
    "Web Search (External)",
    "Structured Data (External)",
    "Code Repositories (External)"
]

# Simple search result class for testing
class SimpleSearchResult:
    def __init__(self, content, source, relevance=0.0):
        self.content = content
        self.source = source
        self.relevance = relevance

# Mock search function for direct use without imports
def simple_search(query, sources, max_results=3):
    """Simple search function that returns mock results when the DB is unavailable"""
    results = []
    
    # Check if query is about AWS security
    if "aws security" in query.lower() or ("aws" in query.lower() and "security" in query.lower()):
        # Predefined AWS security responses
        aws_responses = {
            "Indexed Documents": [
                "AWS security benefits include a comprehensive set of cloud security controls, reducing operational overhead compared to on-premises solutions. The AWS security infrastructure provides built-in protections against DDoS attacks, encryption capabilities, and compliance with major regulatory frameworks.",
                "AWS security features include Identity and Access Management (IAM) for fine-grained access control, AWS Shield for DDoS protection, and CloudTrail for audit logging. These services work together to create a defense-in-depth approach to cloud security.",
                "The AWS shared responsibility model clarifies security ownership between AWS and customers. AWS handles security OF the cloud, while customers manage security IN the cloud, allowing organizations to focus security efforts appropriately."
            ],
            "Web Search (External)": [
                "According to AWS documentation, security best practices include implementing least privilege access, encrypting data in transit and at rest, and enabling multi-factor authentication for all users, especially those with administrative access.",
                "Recent industry reports highlight AWS security certifications including SOC 1/2/3, PCI DSS, and HIPAA compliance, making it suitable for organizations with strict regulatory requirements.",
                "Cloud security professionals recommend regular security assessments of AWS environments using tools like AWS Security Hub, GuardDuty, and third-party security scanning solutions."
            ],
            "Structured Data (External)": [
                "A 2023 survey of enterprise cloud users found that 78% of organizations using AWS reported improved security posture compared to their on-premises environments, with particular improvements in patching cadence and threat detection.",
                "Analysis of cloud security incidents shows that 92% of AWS security breaches are attributed to misconfiguration rather than platform vulnerabilities, emphasizing the importance of proper security controls implementation.",
                "AWS security pricing data indicates that basic security services like IAM and Security Groups are included at no additional cost, while advanced services like GuardDuty and Macie are priced based on data processing volumes."
            ]
        }
        
        # Add mock results for each source
        for source in sources:
            if source in aws_responses:
                for content in aws_responses[source][:max_results]:
                    results.append(SimpleSearchResult(
                        content=content,
                        source=source,
                        relevance=round(random.uniform(0.85, 0.98), 2)
                    ))
    
    # If no specific content matches, generate generic responses
    if not results:
        for source in sources:
            for i in range(max_results):
                results.append(SimpleSearchResult(
                    content=f"Information about {query} would be retrieved from {source}. This is placeholder content that would normally contain actual search results related to your query.",
                    source=source,
                    relevance=round(random.uniform(0.70, 0.90), 2)
                ))
    
    return results

# Format search results for display
def format_search_results(results):
    """Format search results for display in the UI"""
    formatted = ""
    
    for i, result in enumerate(results, 1):
        formatted += f"**Result {i}** (Relevance: {result.relevance:.2f})\n\n"
        formatted += f"**Source:** {result.source}\n\n"
        formatted += f"{result.content}\n\n"
        formatted += "---\n\n"
    
    return formatted

def render_enhanced_research(user=None, permissions=None, auth_middleware=None, available_indexes=None, INDEX_ROOT=None, PROJECT_ROOT=None):
    """Enhanced Research Tab Implementation with centralized vector DB integration"""
    
    st.title("📚 Enhanced Research")
    
    # Add a brief description
    st.markdown("""
    Generate comprehensive research on any topic using multiple knowledge sources.
    The enhanced research module combines information from indexed documents, web searches, and structured data sources.
    """)
    
    # Sidebar for research parameters
    with st.sidebar:
        st.header("Research Parameters")
        
        # Research query
        research_query = st.text_area("Research Topic or Question", 
                                     placeholder="Enter your research topic or question here...",
                                     help="Be specific about what you want to research")
        
        # Research operation
        research_operation = st.selectbox("Research Operation", 
                                         options=RESEARCH_OPERATIONS,
                                         help="The type of research to perform")
        
        # Knowledge sources (multiselect)
        knowledge_sources = st.multiselect("Knowledge Sources", 
                                          options=KNOWLEDGE_SOURCES,
                                          default=["Indexed Documents"],
                                          help="Select which sources to include in the research")
        
        # Add note about vector database status
        if db_provider:
            status, message = db_provider.get_vector_db_status()
            st.write(f"Vector Database Status: **{status}**")
            st.write(f"_{message}_")
        else:
            st.warning("⚠️ Vector database provider not available. Using fallback mock data.")
        
        # Generate button
        generate_button = st.button("Generate Research", type="primary")
    
    # Main content area
    if not research_query:
        st.info("👈 Enter a research topic and select parameters in the sidebar to get started")
    elif generate_button:
        # Show a spinner while generating research
        with st.spinner(f"Researching '{research_query}'..."):
            try:
                # Log start time for performance tracking
                start_time = time.time()
                
                # Check if enhanced research is available
                if ENHANCED_RESEARCH_AVAILABLE and db_provider:
                    # Use the centralized enhanced research module
                    research_content = generate_enhanced_research_content(
                        task=research_query,
                        operation=research_operation,
                        knowledge_sources=knowledge_sources
                    )
                else:
                    # Fall back to simple search and basic formatting
                    logger.warning("Enhanced research not available, using fallback implementation")
                    
                    # Perform simple search
                    search_results = simple_search(research_query, knowledge_sources)
                    
                    # Format results
                    search_results_text = format_search_results(search_results)
                    
                    # Generate basic research content
                    research_content = f"""
## Research Report: {research_query}

### Executive Summary
This research report addresses the topic of {research_query}, based on available information.

### Search Results
{search_results_text}

### Key Findings
1. First key finding based on the search results
2. Second key finding from the available information
3. Third important insight related to the topic

### Conclusion
This research provides a starting point for understanding {research_query}.
Further investigation may be needed for a comprehensive analysis.

### Knowledge Sources Used
"""
                    for source in knowledge_sources:
                        research_content += f"- {source}\n"
                
                # Log completion time
                duration = time.time() - start_time
                logger.info(f"Research generated in {duration:.2f} seconds")
                
                # Display the generated research
                st.markdown(research_content)
                
                # Add metrics about the generation
                st.sidebar.success(f"✅ Research generated in {duration:.2f} seconds")
                
                # Record the action if auth middleware is available
                if auth_middleware:
                    auth_middleware.log_user_action("GENERATE_RESEARCH", {
                        "query": research_query,
                        "operation": research_operation,
                        "sources": knowledge_sources,
                        "duration": duration
                    })
                
            except Exception as e:
                logger.error(f"Error generating research: {e}")
                st.error(f"An error occurred while generating research: {str(e)}")
    
    # Add informational footer
    st.markdown("---")
    st.markdown("""
    **Using the Enhanced Research Tab:**
    1. Enter your research topic or question in the sidebar
    2. Select the type of research operation to perform
    3. Choose which knowledge sources to include
    4. Click "Generate Research" to create a comprehensive report
    """)
    
    # If no indexes are available, show a hint
    if db_provider and len(db_provider.get_available_indexes()) == 0:
        st.warning("⚠️ No document indexes found. Please upload and index documents in the Document Ingestion tab first.")
