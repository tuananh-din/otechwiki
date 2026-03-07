from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
from app.models.user import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(100))
    image_url = Column(String(500))
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    documents = relationship("Document", secondary="document_products", back_populates="products")


document_products = Table(
    "document_products",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)
    source_path = Column(String(1000))
    source_url = Column(String(1000))
    document_type = Column(String(50))
    file_size = Column(BigInteger)
    page_count = Column(Integer)
    status = Column(String(20), default="pending")
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    products = relationship("Product", secondary="document_products", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer)
    section_title = Column(String(500))
    token_count = Column(Integer)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="chunks")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text, nullable=False)
    search_type = Column(String(20))
    results_count = Column(Integer, default=0)
    had_ai_answer = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="search_logs")


# re-export for convenience
from sqlalchemy import Boolean
