from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, ForeignKey, Table, Boolean, Float
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
    Column("matched_by", String(50)),
    Column("confidence", Float, default=1.0),
    Column("review_status", String(20), default="auto"),
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
    # V2 pipeline fields
    raw_text = Column(Text)
    cleaned_text = Column(Text)
    page_type = Column(String(50))  # product_detail, collection, homepage, other
    domain = Column(String(200))
    cleaning_status = Column(String(20), default="pending")  # pending, cleaned, legacy, error

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
    # V2 pipeline fields
    cleaned_content = Column(Text)
    section_path = Column(Text)
    is_searchable = Column(Boolean, default=True)
    dedup_hash = Column(String(64))
    mapping_confidence = Column(Integer)  # stored as Float in DB

    document = relationship("Document", back_populates="chunks")


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(200), nullable=False)
    alias_type = Column(String(50), default="abbreviation")  # abbreviation, nickname, sku, slug

    product = relationship("Product")


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


class AutocompleteEntry(Base):
    __tablename__ = "autocomplete_entries"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False, default="curated")  # curated, popular, product, faq
    query = Column(Text, nullable=False)
    intent = Column(String(50))  # gia_ban, bao_hanh, so_sanh, tinh_nang, thong_so, mua_hang
    priority = Column(Integer, default=5)  # 1-10, higher = shown first
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# re-export for convenience
from sqlalchemy import Boolean
