"""
Pydantic models for API request/response validation.
"""

from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "user"
    department: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class QueryRequest(BaseModel):
    query: str
    department: Optional[str] = None
    top_k: int = 10


class ChatRequest(BaseModel):
    messages: list[dict]
    department: Optional[str] = None


class AccessRequestCreate(BaseModel):
    dept_code: str
    requested_tab: str
    requested_role: str = "user"
    justification: str


class AccessRequestReview(BaseModel):
    request_id: int
    action: str
    note: Optional[str] = None


class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: int
    source: str = "rag"
    dept_code: str = "general"
    comment: Optional[str] = None


class AgentRunRequest(BaseModel):
    query: str
    dept: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_steps: int = 12


class ResearchRequest(BaseModel):
    query: str
    use_internal: bool = True
    use_web: bool = True
    use_cross_dept: bool = False
    use_ai_analysis: bool = True
    dept: Optional[str] = None


class ConversationCreate(BaseModel):
    tab: str = "chat"
    dept: Optional[str] = None
    title: str = "New Conversation"


class MessageAppend(BaseModel):
    role: str
    content: str
    source: Optional[str] = None
    source_label: Optional[str] = None


class McpToolCreate(BaseModel):
    name: str
    category: str = "communication"
    description: str = ""
    tool_type: str
    dept_scope: Optional[str] = None
    min_role: str = "user"
    is_enabled: bool = True


class McpToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dept_scope: Optional[str] = None
    min_role: Optional[str] = None
    is_enabled: Optional[bool] = None


class McpConfigSet(BaseModel):
    dept_code: str
    config: dict


class McpRunRequest(BaseModel):
    tool_id: int
    result_text: str
    query: str
    user_params: dict = {}
