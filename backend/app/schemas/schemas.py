from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    is_admin: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False


class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # 'keyword', 'semantic', 'hybrid'
    product_filter: Optional[str] = None
    doc_type_filter: Optional[str] = None
    limit: int = 10


class ChunkResult(BaseModel):
    id: int
    content: str
    score: float
    document_id: int
    document_title: str
    source_type: str
    page_number: Optional[int]
    section_title: Optional[str]

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkResult]
    total: int


class AskRequest(BaseModel):
    query: str
    product_filter: Optional[str] = None
    doc_type_filter: Optional[str] = None


class Citation(BaseModel):
    document_id: int
    document_title: str
    page_number: Optional[int]
    section_title: Optional[str]
    snippet: str


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
    no_result: bool = False
    answer_type: str = "standard"  # standard, comparison, recommendation
    follow_up_questions: list[str] = []


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    category: Optional[str]
    image_url: Optional[str]
    document_count: int = 0

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    source_type: str
    source_url: Optional[str]
    document_type: Optional[str]
    page_count: Optional[int]
    status: str
    created_at: datetime
    product_names: list[str] = []

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    total_searches: int
    total_documents: int
    total_chunks: int
    top_queries: list[dict]
    no_result_queries: list[dict]
    searches_by_day: list[dict]
