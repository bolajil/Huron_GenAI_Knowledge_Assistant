"""
Quick HR Pilot Index Creator for Huron
Creates FAISS index with sample HR documents embedded inline
"""

import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import pickle

# HR Sample Documents (embedded for reliability)
HR_DOCUMENTS = {
    "HR_Employee_Handbook": """
HURON CONSULTING GROUP
EMPLOYEE HANDBOOK
Version 2026.1

SECTION 2: EMPLOYMENT POLICIES

2.1 Remote Work Policy

Huron Consulting Group supports flexible work arrangements including remote work and hybrid schedules. Employees may work remotely up to 3 days per week with manager approval. Full-time remote work requires VP-level approval and must be documented in the employee's file.

Remote Work Requirements:
- Reliable high-speed internet connection
- Dedicated workspace free from distractions
- Available during core business hours (9 AM - 3 PM local time)
- Must attend mandatory in-person meetings quarterly
- All work must be performed within the United States unless otherwise approved

Hybrid Schedule Options:
- Standard Hybrid: 2 days office, 3 days remote
- Flexible Hybrid: 3 days office, 2 days remote
- Office-First: 4 days office, 1 day remote

SECTION 3: CODE OF CONDUCT

3.1 Professional Behavior Standards

All employees are expected to:
- Act with integrity and honesty in all business dealings
- Treat colleagues, clients, and partners with respect and dignity
- Maintain confidentiality of company and client information
- Avoid conflicts of interest
- Comply with all applicable laws and regulations
- Report any suspected violations through proper channels

SECTION 4: BENEFITS OVERVIEW

4.1 Health Insurance

Huron offers comprehensive health insurance benefits effective the first of the month following your start date:

Medical Plans:
- PPO Plan: $150/month employee only, $400/month family
- HDHP with HSA: $75/month employee only, $200/month family
- Company HSA contribution: $500 individual, $1000 family annually

Dental Coverage:
- Preventive care: 100% covered
- Basic procedures: 80% covered
- Major procedures: 50% covered
- Annual maximum: $2,000

Vision Coverage:
- Eye exam: $10 copay
- Frames: $150 allowance every 24 months
- Contact lenses: $150 allowance annually

4.2 401(k) Retirement Plan

- Eligible after 90 days of employment
- Company match: 100% of first 3%, 50% of next 2%
- Immediate vesting on employee contributions
- Company match vests over 4 years (25% per year)
- Pre-tax and Roth options available

SECTION 5: TIME OFF AND LEAVE POLICIES

5.1 Paid Time Off (PTO)

Vacation days are based on years of service:
- 0-2 years: 15 days (120 hours)
- 3-5 years: 20 days (160 hours)
- 6-10 years: 25 days (200 hours)
- 10+ years: 30 days (240 hours)

PTO accrues bi-weekly. Maximum carryover is 5 days. Unused PTO above carryover limit is forfeited on December 31.

5.2 Leave Request Process

To request time off:
1. Submit request through Workday at least 2 weeks in advance
2. Manager approval required within 5 business days
3. Requests over 5 consecutive days require director approval
4. Emergency leave requests should notify manager immediately

5.3 Parental Leave

Primary Caregiver Leave: 16 weeks paid at 100% salary
Secondary Caregiver Leave: 6 weeks paid at 100% salary

Additional unpaid leave up to 12 weeks may be requested under FMLA. Parental leave must be taken within 12 months of birth or adoption.

SECTION 6: PERFORMANCE MANAGEMENT

6.1 Performance Review Process

Annual performance reviews are conducted in January-February:

Timeline:
- December: Self-assessment completion
- January: Manager evaluation and calibration
- February: Performance discussion and feedback
- March: Goal setting for upcoming year

Rating Scale:
- Exceptional: Consistently exceeds all expectations
- Strong: Frequently exceeds expectations
- Effective: Meets all expectations
- Developing: Meeting some expectations, improvement needed
- Unsatisfactory: Not meeting expectations

SECTION 7: EXPENSE REIMBURSEMENT

7.1 Submitting Expense Reports

To submit expenses for reimbursement:
1. Log into Concur expense system
2. Create new expense report within 30 days of expense
3. Attach original receipts for all expenses over $25
4. Select appropriate expense category
5. Submit for manager approval
6. Reimbursement processed within 2 pay periods

Allowable Expenses:
- Business travel (airfare, hotel, rental car, meals)
- Client entertainment (pre-approval required over $100)
- Professional development and training
- Office supplies for remote work (up to $500/year)
- Cell phone reimbursement ($75/month if required for work)
""",

    "HR_Organizational_Structure": """
HURON CONSULTING GROUP
ORGANIZATIONAL STRUCTURE
Effective January 2026

EXECUTIVE LEADERSHIP

Chief Executive Officer (CEO)
- Chief Operating Officer (COO)
- Chief Financial Officer (CFO)
- Chief Human Resources Officer (CHRO)
- Chief Technology Officer (CTO)
- General Counsel

BUSINESS SEGMENTS

Healthcare Segment
- Healthcare Performance Improvement
- Healthcare Technology
- Healthcare Analytics

Education Segment
- Higher Education Strategy
- K-12 Advisory
- Research Compliance

Commercial Segment
- Financial Services
- Energy & Utilities
- Life Sciences

CORPORATE FUNCTIONS

Human Resources
- Talent Acquisition
- HR Business Partners
- Benefits & Compensation
- Learning & Development
- HR Operations

Finance & Accounting
- Financial Planning & Analysis
- Accounting Operations
- Tax
- Treasury

Information Technology
- Enterprise Applications
- Infrastructure & Security
- Data & Analytics
- Client Technology Services

REPORTING STRUCTURE

All employees report through their functional hierarchy:
Individual Contributors → Manager → Director → VP → SVP → C-Suite

Matrix reporting may apply for project-based work where employees report to both:
- Functional Manager (career development, performance)
- Project Lead (day-to-day work direction)
""",

    "HR_Training_Programs": """
HURON CONSULTING GROUP
TRAINING AND DEVELOPMENT PROGRAMS
2026 Catalog

ONBOARDING PROGRAMS

New Hire Orientation (Required - Week 1)
- Company history and culture
- Systems and tools training
- Compliance and ethics training
- Benefits enrollment assistance
Duration: 2 days

Consultant Foundations (Required - Month 1)
- Consulting methodology
- Client engagement protocols
- Project management basics
- Communication skills
Duration: 5 days

PROFESSIONAL DEVELOPMENT

Leadership Development Program
- Target: Senior Consultants and above
- Topics: Strategic thinking, team leadership, executive presence
- Format: Monthly workshops + coaching
- Duration: 12 months

Project Management Certification
- Target: All consultants
- Certification: PMP preparation
- Format: Self-paced + instructor-led sessions
- Duration: 3 months

Data Analytics Bootcamp
- Target: All employees
- Topics: SQL, Tableau, Python basics
- Format: Virtual instructor-led
- Duration: 40 hours

COMPLIANCE TRAINING (REQUIRED ANNUALLY)

- Information Security Awareness
- Anti-Harassment and Discrimination
- Code of Ethics Review
- Data Privacy and HIPAA (Healthcare roles)
- Insider Trading Prevention

TUITION REIMBURSEMENT

Eligibility: Employees with 1+ year tenure
Maximum: $5,250/year for undergraduate, $10,000/year for graduate
Requirements:
- Degree program related to current or future role
- Pre-approval required
- Maintain B average or equivalent
- Remain employed 12 months post-completion

APPLICATION PROCESS

1. Discuss development goals with manager
2. Submit training request through Workday Learning
3. Manager approval required within 10 days
4. HR Learning & Development confirmation
5. Complete training and submit certificate/proof

Contact: learning@huron.com
"""
}


def create_hr_index():
    """Create HR Pilot FAISS index"""
    print("=" * 50)
    print("HR PILOT INDEX CREATOR - HURON")
    print("=" * 50)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(".env")
        load_dotenv("config/storage.env")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found. Set it in .env file.")
        return False
    
    # Initialize embeddings
    print("\n1. Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    
    # Create documents
    print("2. Creating document chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    all_docs = []
    for doc_name, content in HR_DOCUMENTS.items():
        chunks = text_splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": doc_name,
                    "chunk_id": i,
                    "dept_id": "hr",
                    "document_type": "hr_policy" if "Handbook" in doc_name else "hr_reference"
                }
            )
            all_docs.append(doc)
    
    print(f"   Created {len(all_docs)} chunks from {len(HR_DOCUMENTS)} documents")
    
    # Create FAISS index
    print("3. Creating FAISS index...")
    vectorstore = FAISS.from_documents(all_docs, embeddings)
    
    # Save index
    index_path = Path(__file__).parent.parent / "data" / "faiss_index" / "HR_Pilot_index"
    index_path.mkdir(parents=True, exist_ok=True)
    
    print(f"4. Saving index to {index_path}...")
    vectorstore.save_local(str(index_path))
    
    # Also save documents for retrieval
    docs_path = index_path / "documents.pkl"
    with open(docs_path, "wb") as f:
        pickle.dump(all_docs, f)
    
    print("\n" + "=" * 50)
    print("SUCCESS! HR Pilot index created")
    print("=" * 50)
    print(f"\nIndex location: {index_path}")
    print(f"Total chunks: {len(all_docs)}")
    print(f"Documents: {list(HR_DOCUMENTS.keys())}")
    
    # Test query
    print("\n5. Testing retrieval...")
    test_query = "What is the remote work policy?"
    results = vectorstore.similarity_search(test_query, k=3)
    print(f"\nQuery: '{test_query}'")
    print(f"Top result: {results[0].page_content[:200]}...")
    
    return True


if __name__ == "__main__":
    success = create_hr_index()
    sys.exit(0 if success else 1)
