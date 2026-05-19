"""
VaultMind GenAI Knowledge Assistant - FastAPI Backend
Following FRONTEND_MIGRATION_GUIDE.md Option 3: FastAPI + React
Standalone version without Streamlit dependencies
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uvicorn
import jwt
import bcrypt
import sqlite3
from pathlib import Path

# VaultMind imports for real pipeline
import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.tenant_context import TenantContext
from utils.ingestion_service import IngestionService
from utils.rag_orchestrator import RAGOrchestrator

# Lazy-loaded singletons
_ingestion_service = None
_rag_orchestrator = None

def get_ingestion_service():
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService(
            enable_pinecone=True,
            enable_dlp_scan=True,
            enable_quality_gate=True,
            enable_classification=False,
            pinecone_index=os.getenv('PINECONE_INDEX', 'huron-enterprise-knowledge'),
        )
    return _ingestion_service

def get_rag_orchestrator():
    global _rag_orchestrator
    if _rag_orchestrator is None:
        _rag_orchestrator = RAGOrchestrator(
            pinecone_index=os.getenv('PINECONE_INDEX', 'huron-enterprise-knowledge'),
        )
    return _rag_orchestrator
app = FastAPI(
    title="VaultMind GenAI Knowledge Assistant API",
    description="Enterprise AI-powered knowledge management API",
    version="1.0.0"
)

# CORS for React frontend (allow all localhost ports during development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT Settings
SECRET_KEY = "vaultmind-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "users.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============== Standalone Auth ==============

def init_db():
    """Initialize user database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            department TEXT DEFAULT 'general',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create default admin if not exists (per TRANSFORMATION_PLAN.md)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b"VaultMind2025!", bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, department) VALUES (?, ?, ?, ?, ?)",
            ("admin", "admin@vaultmind.ai", password_hash, "admin", "IT")
        )
    conn.commit()
    conn.close()


def authenticate_user(username: str, password: str):
    """Authenticate user against database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, password_hash, role, department FROM users WHERE username = ? OR email = ?",
        (username, username)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    user_id, user_name, email, password_hash, role, department = row
    
    if bcrypt.checkpw(password.encode(), password_hash.encode()):
        return {
            "id": str(user_id),
            "username": user_name,
            "email": email,
            "role": role,
            "department": department
        }
    return None


def create_token(user: dict) -> str:
    """Create JWT token with department namespace isolation"""
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    # Map role to clearance level for namespace access control
    clearance_map = {
        "admin": 4,      # Full access to all namespaces
        "power_user": 3, # Extended access with cross-dept queries
        "user": 2,       # Standard dept-scoped access
        "viewer": 1      # Read-only dept-scoped access
    }
    
    payload = {
        "sub": user["username"],
        "email": user["email"],
        "role": user["role"],
        "dept_id": user.get("department", "general"),  # Department namespace isolation
        "clearance_level": clearance_map.get(user["role"], 2),  # Access level
        "namespace_scope": [user.get("department", "general")],  # Allowed namespaces
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Initialize database on startup
init_db()


# ============== Pydantic Models ==============

class LoginRequest(BaseModel):
    username: str
    password: str
    auth_method: str = "local"
    remember_me: bool = False
    trust_device: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class QueryRequest(BaseModel):
    query: str
    index_name: str = "default_faiss"
    top_k: int = 5
    department: Optional[str] = None


class QueryResponse(BaseModel):
    status: str
    query: str
    results: str
    sources: List[dict] = []


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    index_name: str = "default_faiss"
    department: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    department: str
    role: str
    permissions: List[str]


# ============== Auth Endpoints ==============

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate JWT token
    token = create_token(user)
    
    return LoginResponse(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["username"].title(),
            "department": user["department"],
            "role": user["role"],
            "permissions": _get_user_permissions(user["role"])
        }
    )


@app.get("/api/v1/auth/validate")
async def validate_token_endpoint(token: str = Depends(oauth2_scheme)):
    """Validate JWT token"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return {"valid": True, "user": payload["sub"]}


@app.post("/api/v1/auth/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Logout user (invalidate token)"""
    # Token invalidation logic here
    return {"message": "Logged out successfully"}


# ============== Query Endpoints ==============

@app.post("/api/v1/query", response_model=QueryResponse)
async def query(request: QueryRequest, token: str = Depends(oauth2_scheme)):
    """Execute a knowledge base query"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # TODO: Integrate with actual search when backend is connected
    return QueryResponse(
        status="success",
        query=request.query,
        results=f"Search results for: {request.query}\n\nThis is a placeholder response. Connect to the actual VaultMind search backend for real results.",
        sources=[]
    )


# ============== Chat Endpoints ==============

@app.post("/api/v1/chat")
async def chat(request: ChatRequest, token: str = Depends(oauth2_scheme)):
    """Handle chat conversation"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get the latest user message
    user_message = request.messages[-1].content if request.messages else ""
    
    # TODO: Integrate with LLM for chat response
    return {
        "status": "success",
        "response": f"I received your message: '{user_message}'\n\nThis is a placeholder response. Connect to the actual VaultMind chat backend for real AI responses.",
        "sources": []
    }


# ============== Ingestion Endpoints ==============

@app.post("/api/v1/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    index_name: str = Form("default_faiss"),
    department: str = Form(None),
    token: str = Depends(oauth2_scheme)
):
    """Upload and ingest a document"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        # Save uploaded file temporarily
        content = await file.read()
        
        # TODO: Use existing ingestion pipeline
        # from tabs.document_ingestion import process_document
        
        return {
            "status": "success",
            "message": f"Document {file.filename} queued for processing",
            "index_name": index_name,
            "department": department
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Admin Endpoints ==============

@app.get("/api/v1/admin/users")
async def list_users(token: str = Depends(oauth2_scheme)):
    """List all users (admin only)"""
    payload = verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, department, is_active FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    users = [
        {"id": r[0], "username": r[1], "email": r[2], "role": r[3], "department": r[4], "is_active": bool(r[5])}
        for r in rows
    ]
    return {"users": users}


@app.get("/api/v1/admin/stats")
async def get_stats(token: str = Depends(oauth2_scheme)):
    """Get system statistics"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # TODO: Get actual stats from system
    return {
        "total_documents": 2847,
        "queries_today": 1429,
        "active_users": 342,
        "avg_response_time": 1.2
    }


# ============== Index Management Endpoints ==============

@app.get("/api/v1/indexes")
async def list_indexes():
    """
    List all available FAISS indexes.
    Discovers indexes from data/faiss_index directory.
    """
    from pathlib import Path
    import pickle as pkl
    
    indexes = []
    faiss_dir = Path(__file__).parent.parent / "data" / "faiss_index"
    
    if faiss_dir.exists():
        for item in faiss_dir.iterdir():
            if item.is_dir():
                # Check for index files
                has_faiss = (item / "index.faiss").exists()
                has_pkl = (item / "index.pkl").exists() or (item / "documents.pkl").exists()
                
                if has_faiss or has_pkl:
                    # Calculate size
                    size_bytes = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Count documents
                    doc_count = 0
                    for pkl_name in ["documents.pkl", "index.pkl"]:
                        pkl_file = item / pkl_name
                        if pkl_file.exists():
                            try:
                                with open(pkl_file, 'rb') as f:
                                    docs = pkl.load(f)
                                    doc_count = len(docs) if isinstance(docs, list) else 0
                                break
                            except:
                                pass
                    
                    indexes.append({
                        "name": item.name,
                        "type": "FAISS",
                        "documents": doc_count,
                        "size_mb": round(size_mb, 2),
                        "status": "active"
                    })
    
    indexes.sort(key=lambda x: x["name"])
    
    return {
        "status": "success",
        "count": len(indexes),
        "indexes": indexes
    }


# ============== Health Check ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "VaultMind API"}


# ============== Helper Functions ==============

def _get_user_permissions(role: str) -> List[str]:
    """Get permissions based on role"""
    base_permissions = ["query", "chat"]
    
    if role == "admin":
        return base_permissions + ["admin", "ingest", "manage_users", "manage_departments"]
    elif role == "user":
        return base_permissions + ["ingest"]
    else:
        return base_permissions


# ============== Run Server ==============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
