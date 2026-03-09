# 📜 Knowledge Search — Lịch sử phát triển

Tài liệu này ghi lại toàn bộ quá trình phát triển ứng dụng **Knowledge Search (OtechWiki)**.
Dùng để handover cho máy mới hoặc developer mới tiếp tục phát triển.


---

## 🏗️ Tổng quan kiến trúc

| Layer | Tech | Mô tả |
|-------|------|--------|
| *Frontend* | Next.js (TypeScript) | SaaS UI, glassmorphism, Poppins/Inter fonts |
| *Backend* | FastAPI (Python 3.11) | REST API, async, RAG pipeline |
| *Database* | PostgreSQL 16 + pgvector + pg_trgm | Vector search, full-text search, fuzzy matching |
| *AI* | OpenAI API | Embeddings + GPT synthesis + structured extraction |
| *Deploy* | Docker Compose | 5 services: db, backend, frontend, tunnel_be, tunnel_fe |

### Repo GitHub

https://github.com/tuananh-din/otechwiki.git

---

## 📁 Cấu trúc dự án hiện tại

### Backend (backend/app/)

| File | Chức năng |
|------|-----------|
| main.py | FastAPI app entry point |
| api/auth.py | JWT authentication, login |
| api/documents.py | CRUD documents, bulk delete, ingest, import |
| api/search.py | Search endpoint, AI synthesis |
| core/config.py | App config from .env |
| core/database.py | PostgreSQL async connection |
| core/security.py | JWT token, password hashing |
| models/document.py | SQLAlchemy models: Document, Chunk, Product, ProductAlias |
| models/user.py | User model |
| schemas/schemas.py | Pydantic schemas (request/response) |
| services/ingest.py | Web page ingestion (fetch + extract + chunk + embed) |
| services/discovery.py | Auto-discover sub-pages from a root URL |
| services/search.py | Vector similarity search + full-text |
| services/rag.py | RAG pipeline: retrieve → synthesize with GPT (fuzzy ILIKE match, structured metadata injection) |
| services/query_understanding.py | Intent classification + typo correction (corrected_query) |
| services/follow_up.py | Rule-based follow-up question generation |
| services/embeddings.py | OpenAI embeddings wrapper |
| services/cleaner.py | HTML boilerplate removal (30+ patterns) |
| services/chunker_v2.py | Heading-aware text chunking |
| services/dedup.py | URL/block/chunk deduplication |
| services/mapper_v2.py | Multi-source product mapping with aliases |
| services/product_mapper.py | Product name extraction from content |
| services/import_jobs.py | Background async import with progress tracking |
| services/autocomplete.py | Search autocomplete suggestions |
| services/seed_autocomplete.py | Seed autocomplete from existing data |
| services/url_utils.py | URL normalization, tracking param stripping, blacklist |
| services/completeness.py | Completeness scoring per page type (0-100) |

### Backend — Scripts gốc (backend/)

| File | Chức năng |
|------|-----------|
| reprocess_all.py | Reprocess toàn bộ documents qua pipeline V2 |
| extract_products.py | GPT-4o-mini structured extraction (price, specs, features) |
| deep_crawl.py | Deep crawl toàn bộ subpages (depth 5, max 500 URLs) |
| migrate_sprint1.py | Migration: enable pg_trgm + trigram indexes |
| migrate_sprint2.py | Migration: incremental pipeline columns + indexes |
| incremental_import.py | Incremental import orchestrator (discover → compare → upsert) |
| smart_recrawl.py | Smart recrawl policy (freshness decay + auto-recrawl stale) |
| analytics_report.py | Import analytics + coverage report |
| reset_admin.py | Admin password reset |
| init.sql | SQL khởi tạo database schema |

### Frontend (frontend/src/)

| File | Chức năng |
|------|-----------|
| app/page.tsx | Homepage / landing |
| app/search/page.tsx | AI search page (main feature) |
| app/documents/page.tsx | Document list + bulk delete |
| app/documents/[id]/page.tsx | Document detail view |
| app/products/page.tsx | Product catalog |
| app/products/[slug]/page.tsx | Product detail |
| app/recent/page.tsx | Recently viewed |
| app/login/page.tsx | Login page |
| app/admin/page.tsx | Admin dashboard |
| app/admin/data-sources/page.tsx | Data source management + import |
| app/admin/cleaning-dashboard/page.tsx | Content cleaning monitor |
| app/admin/product-mapping/page.tsx | Product mapping config |
| app/admin/autocomplete-config/page.tsx | Autocomplete configuration |
| app/admin/analytics/page.tsx | Usage analytics |
| components/AppLayout.tsx | Shared layout (sidebar, header) |
| lib/api.ts | API client (axios) |

---

## 🕐 Lịch sử phát triển theo thứ tự

### Phase 1: Foundation (Commit f9cfed2 → 41a059e)

*Mục tiêu:* Xây dựng nền tảng ứng dụng.

- ✅ Khởi tạo project
- ✅ Backend FastAPI + PostgreSQL pgvector
- ✅ Frontend Next.js
- ✅ Docker Compose (3 services: db, backend, frontend)
- ✅ Dockerfiles cho backend (Python 3.11-slim) và frontend (Node 20-alpine, multi-stage build)
- ✅ JWT Authentication (login, register)
- ✅ Document CRUD (upload, list, view, delete)
- ✅ Web page ingestion (fetch URL → extract text → chunk → embed → store)
- ✅ Vector similarity search

### Phase 2: Bug Fixes & Config (Commit 48893ec → 26f3748)

- ✅ Fix frontend port 3000 → 3001 (tránh conflict)
- ✅ Fix CORS origins cho cross-origin requests
- ✅ Fix API URL build-arg cho frontend Docker
- ✅ Thêm admin password reset script (reset_admin.py)
- ✅ CORS cho phép tất cả origins (dev mode)
- ✅ Cấu hình Cloudflare Tunnel cho public access
- ✅ Thêm dependency markitdown

### Phase 3: SaaS UI Redesign (Commit 77b7c94)

*Mục tiêu:* Chuyển UI từ basic → professional SaaS.

- ✅ *Design System:* Glassmorphism, backdrop-blur, semi-transparent cards
- ✅ *Color Palette:* Blue-based (#0ea5e9 primary), dark background
- ✅ *Typography:* Poppins (headings) + Inter (body) từ Google Fonts
- ✅ *Icons:* Chuyển sang Lucide React SVG icons
- ✅ *Layout:* Responsive sidebar, mobile hamburger menu
- ✅ *Components:* Cards, badges, search bars với glassmorphism style

### Phase 4: Enhanced Web Crawler (Commit ea07da3 — phần 1)

*Mục tiêu:* Crawl sâu hơn, import nhanh hơn.

- ✅ Tăng page limit 60 → 200
- ✅ Thêm Chrome User-Agent header (bypass 403 blocks)
- ✅ *Discovery service* (discovery.py): auto-discover sub-pages từ root URL
- ✅ *Background import* (import_jobs.py): async import với progress tracking
- ✅ API endpoints: POST /admin/start-import, GET /admin/import-job/{id}
- ✅ Frontend: progress bar (polling 2s), select-all toggle, re-import badge

### Phase 5: Ingest Pipeline V2 (Commit ea07da3 — phần 2)

*Mục tiêu:* Cải thiện chất lượng data ingestion.

- ✅ *Schema migration:* Thêm raw_text, cleaned_text, page_type, is_searchable, dedup_hash, bảng product_aliases
- ✅ *Cleaner* (cleaner.py): BS4 boilerplate removal, 30+ pattern (ratings, colors, share buttons, footers)
- ✅ *Chunker V2* (chunker_v2.py): Heading-aware chunking, tách theo section
- ✅ *Dedup* (dedup.py): URL-level, block-level, chunk-level deduplication
- ✅ *Mapper V2* (mapper_v2.py): Multi-source confidence mapping với product aliases
- ✅ *Search update:* Dùng cleaned_content + is_searchable filter

### Phase 6: AI Search Features (Commit ea07da3 — phần 3)

*Mục tiêu:* Search thông minh hơn với AI.

- ✅ *Intent Classification* (query_understanding.py): Phân loại query thành comparison, recommendation, specs, warranty, troubleshooting, price, general
- ✅ *AI Synthesis* (rag.py): Structured prompts cho comparison table, recommendation list, specs extraction
- ✅ *Follow-up Questions* (follow_up.py): Rule-based templates theo intent + product, zero token cost
- ✅ *Multi-query retrieval:* Cho policy/troubleshooting/specs intents (fix bug single query match sai page)

### Phase 7: Document Management (Commit ea07da3 — phần 4)

- ✅ *Single delete:* DELETE /api/documents/{id}
- ✅ *Bulk delete:* POST /api/documents/bulk-delete
- ✅ *Duplicate prevention:* 409 trên ingest-web duplicate URL, 409 trên upload duplicate title
- ✅ Frontend: checkbox multi-select, select all, bulk delete confirm dialog
- ✅ DB CASCADE: chunks + product links tự cleanup

### Phase 8: Data Pipeline Fix & Product Extraction (2026-03-09)

*Mục tiêu:* Fix empty products & product mapping, extract structured data.

- ✅ *API Proxy Fix:* Next.js rewrites thay thế direct API URL → fix connection issues qua Cloudflare Tunnel
- ✅ *Cleaning Dashboard UI Fix:* Refactored dùng AppLayout + project CSS conventions (globals.css)
- ✅ *Product Creation:* Chạy auto_create_products() → tạo 30 products từ document titles
- ✅ *Product Mapping:* Chạy auto_map_documents() → map 57/60 documents
- ✅ *V2 Pipeline Reprocess:* Reprocess 60/60 documents → heading-aware chunking (183 → 831 chunks)
- ✅ *GPT Structured Extraction:* extract_products.py dùng GPT-4o-mini extract price, specs, features cho 59/59 documents

### Phase 9: Deep Crawl & AI Synthesis Fix (2026-03-09)

*Mục tiêu:* Import toàn bộ subpages, fix AI search.

- ✅ *pg_trgm Extension:* Enable PostgreSQL trigram extension + indexes cho fuzzy matching
- ✅ *RAG Fuzzy Match:* Replace exact alias match (LOWER = LOWER) → ILIKE pattern matching trong rag.py
- ✅ *Structured Metadata Injection:* Thêm _get_product_metadata_context() → inject price/specs/features vào RAG context
- ✅ *Typo Correction:* Thêm corrected_query vào query_understanding.py (robrock → Roborock)
- ✅ *Deep Crawl:* Crawl roborock.com.vn depth=5 → phát hiện **295 URLs mới**
- ✅ *Full Import:* Import qua V2 pipeline → **495 total documents, 12,808 chunks**
- ✅ *Auto-mapping:* **45 products, 194 aliases**
- ✅ *GPT Extraction:* Extract structured data cho **107/107 product detail pages**
- ✅ *Verified:* "robrock f25 gia" → "Giá bán Roborock F25 là 6.990.000₫" ✓

### Phase 10: Incremental Pipeline Foundation (2026-03-09)

*Mục tiêu:* Skip unchanged documents on re-import, save embedding costs.

- ✅ *Schema:* 10 new columns: canonical_url, raw_hash, clean_hash, etag, last_modified_header, completeness_score, freshness_score, last_fetched_at, import_status
- ✅ *URL Utils:* url_utils.py — normalize URLs (strip tracking params, fragments, trailing slash), blacklist paths (/cart, /checkout, /login)
- ✅ *Change Detection:* 2-level hash in ingest.py: raw_hash (skip if HTML identical) → clean_hash (skip if content same despite template change)
- ✅ *Discovery Upgrade:* depth 2→5, branching factor 20→100, integrated URL blacklist
- ✅ *Migration:* Columns added, indexes created, canonical_url backfilled for 495 existing docs
- ✅ *Deployed:* git push → git pull → docker compose build

### Phase 11: Quality & Completeness Scoring (2026-03-09)

*Mục tiêu:* Score document quality, orchestrate incremental imports.

- ✅ *Completeness Scorer:* completeness.py — scores 0-100 per page type (product: price/specs/features/warranty/FAQ checks)
- ✅ *Pipeline Integration:* completeness_score computed during ingest and stored in documents table
- ✅ *Incremental Import:* incremental_import.py orchestrator — discover URLs, compare by canonical_url, import only new/changed, auto-map to products
- ✅ *Deployed:* git push → git pull → docker compose build

### Phase 12: Cross-page Dedup, Smart Recrawl & Analytics (2026-03-09)

*Mục tiêu:* Hoàn thiện các tính năng còn lại từ plan.

- ✅ *Cross-page Dedup:* Thêm `cross_page_dedup()` vào dedup.py — phát hiện shared text (warranty, shipping) xuất hiện ≥3 docs, mark duplicates non-searchable
- ✅ *Smart Recrawl:* smart_recrawl.py — freshness decay (-5/ngày), tự động tìm stale pages và re-import
- ✅ *Analytics Report:* analytics_report.py — coverage dashboard (documents, page types, chunks, freshness, quality issues)
- ✅ *Integrated:* Cross-page dedup chạy tự động cuối mỗi incremental import
- ✅ *Deployed & Verified:* Analytics report chạy thành công trên server

---

## 🐛 Các bug đã fix (quan trọng)

### Bug 1: Frontend gọi API sai URL
- *Vấn đề:* docker-compose.yml có NEXT_PUBLIC_API_URL trỏ Cloudflare tunnel thay vì localhost:8000
- *Hậu quả:* Frontend gọi backend cũ, không có features mới
- *Fix:* Sửa thành http://localhost:8000

### Bug 2: Search bị hỏng sau V2 pipeline reprocess
- *Vấn đề:* 3 bugs cùng lúc:
  1. cleaner.py missed boilerplate noise
  2. chunker_v2.py set cleaned_content == content (bao gồm [Title] prefix) → embedding sai
  3. RAG dùng single query → warranty query match product pages thay vì policy pages
- *Fix:* Sửa cả 3: thêm 30+ patterns cleaner, fix chunker dùng pure text, thêm multi-query retrieval

### Bug 3: Web crawler bị 403
- *Vấn đề:* Một số trang web block requests không có User-Agent
- *Fix:* Thêm Chrome User-Agent header vào discovery.py và ingest.py

### Bug 4: API Proxy qua Cloudflare Tunnel (Phase 8)
- *Vấn đề:* Frontend trong Docker gọi http://localhost:8000 → không thể reach backend container
- *Hậu quả:* Tất cả API calls fail khi deploy qua Cloudflare Tunnel
- *Fix:* Implement Next.js rewrites proxy pattern: frontend → same origin /api/* → backend container. Xóa NEXT_PUBLIC_API_URL từ Dockerfile và docker-compose.yml

### Bug 5: Cleaning Dashboard UI trống (Phase 8)
- *Vấn đề:* Page dùng raw Tailwind CSS classes, không có AppLayout
- *Fix:* Refactored dùng AppLayout component + project CSS conventions (globals.css .card, .stat-card, .grid-3)

### Bug 6: AI Synthesis trả lời "Không tìm thấy" (Phase 9)
- *Vấn đề:* RAG price_lookup dùng exact alias match: `LOWER(pa.alias) = LOWER(:product_name)` → fail khi tên sản phẩm hơi khác
- *Hậu quả:* "robrock f25 gia" (typo nhẹ) → zero chunks → "Không tìm thấy"
- *Fix:* Replace bằng ILIKE fuzzy matching + inject structured metadata từ products.metadata JSONB

### Bug 7: similarity() crash DB transaction (Phase 9)
- *Vấn đề:* Dùng pg_trgm similarity() function trong SQLAlchemy async query → InFailedSQLTransactionError
- *Hậu quả:* Toàn bộ search API trả về empty
- *Fix:* Replace similarity() bằng ILIKE pattern matching (an toàn hơn qua asyncpg)

---

## ⚙️ Cấu hình quan trọng

### File .env backend (KHÔNG có trên GitHub)

```env
DATABASE_URL=postgresql+asyncpg://ks_admin:ks_secret_2024@db:5432/knowledge_search
SECRET_KEY=<random-secret-key>
OPENAI_API_KEY=sk-...
DEBUG=false
WEB_EXTRACTOR_URL=
```

⚠️ Khi chạy Docker: host DB phải là `db` (tên service). Khi chạy local: dùng `localhost`.


### Docker Compose ports

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| Backend API | 8000 |
| Frontend | 3001 → 3000 (internal) |

### PostgreSQL Extensions

| Extension | Chức năng |
|-----------|-----------|
| pgvector | Vector similarity search (embeddings) |
| pg_trgm | Trigram matching cho fuzzy search |

---

## 📊 Số liệu hiện tại (2026-03-09)

| Metric | Giá trị |
|--------|---------|
| Total Documents | 495 |
| Total Chunks | 12,808 |
| Products | 45 |
| Product Aliases | 194 |
| Product Detail Pages | 107 |
| Blog/News Pages | 359 |
| Collection Pages | 27 |
| Pages with Error | 1 |

---

## 📋 Những việc CÓ THỂ cần làm tiếp

⚠️ Đây là gợi ý, chưa implement.

- [x] Incremental pipeline (hash-based change detection, skip unchanged docs)
- [x] URL normalization + canonical URLs
- [x] Completeness scoring per document
- [x] Cross-page dedup (shared warranty text)
- [x] Smart recrawl policy (auto-recrawl stale pages)
- [x] Analytics import reports
- [ ] Semantic fingerprinting (embedding-based near-duplicate)
- [ ] Product autocomplete integration hoàn chỉnh
- [ ] Product mapping UI hoàn thiện
- [ ] Analytics dashboard data thực
- [ ] Caching layer cho search results
- [ ] Rate limiting cho API
- [ ] WebSocket real-time import progress (thay polling)
- [ ] PDF/DOCX upload parsing cải thiện
- [ ] Multi-tenant support
- [ ] Deploy lên Linux server (guide có ở docs/GUIDE-deploy-server.md)

---

## 🔗 Tài liệu liên quan

| File | Nội dung |
|------|----------|
| docs/GUIDE-deploy-server.md | Hướng dẫn deploy lên Linux server |
| backend/.env.example | Template biến môi trường backend |
| backend/init.sql | SQL khởi tạo database schema |
| backend/reprocess_all.py | Script reprocess toàn bộ documents qua pipeline V2 |
| backend/deep_crawl.py | Deep crawl toàn bộ subpages từ root URL |
| backend/extract_products.py | GPT structured extraction cho product pages |
| backend/migrate_sprint1.py | Migration: pg_trgm extension + indexes |
| backend/migrate_sprint2.py | Migration: incremental pipeline columns |

---

Cập nhật lần cuối: 2026-03-09
