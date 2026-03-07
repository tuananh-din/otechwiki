-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    image_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'pdf', 'web'
    source_path VARCHAR(1000),
    source_url VARCHAR(1000),
    document_type VARCHAR(50), -- 'product_spec', 'faq', 'policy', etc.
    file_size BIGINT,
    page_count INT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'ready', 'error'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document-Product junction
CREATE TABLE document_products (
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, product_id)
);

-- Chunks table (core for search + RAG)
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INT NOT NULL,
    page_number INT,
    section_title VARCHAR(500),
    token_count INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search logs
CREATE TABLE search_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    query TEXT NOT NULL,
    search_type VARCHAR(20), -- 'keyword', 'semantic', 'hybrid'
    results_count INT DEFAULT 0,
    had_ai_answer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_chunks_fts ON chunks USING gin (to_tsvector('simple', content));
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_search_logs_user ON search_logs(user_id);
CREATE INDEX idx_search_logs_created ON search_logs(created_at DESC);
CREATE INDEX idx_products_slug ON products(slug);

-- Default admin user (password: admin123 - change on first login!)
INSERT INTO users (username, password_hash, full_name, is_admin)
VALUES ('admin', '$2b$12$LJ3m4ks6Q1Q7q9Y0VkYzXO8HjKJHv0vHo3O6X5pBv4MVjQ8.8yFfm', 'Administrator', TRUE);
