# 📜 Knowledge Search — Lịch sử phát triển

> Tài liệu này ghi lại toàn bộ quá trình phát triển ứng dụng **Knowledge Search (OtechWiki)**.
> Dùng để handover cho máy mới hoặc developer mới tiếp tục phát triển.

---

## 🏗️ Tổng quan kiến trúc

| Layer | Tech | Mô tả |
|-------|------|--------|
| **Frontend** | Next.js (TypeScript) | SaaS UI, glassmorphism, Poppins/Inter fonts |
| **Backend** | FastAPI (Python 3.11) | REST API, async, RAG pipeline |
| **Database** | PostgreSQL 16 + pgvector | Vector search, full-text search |
| **AI** | OpenAI API | Embeddings + GPT synthesis |
| **Deploy** | Docker Compose | 3 services: db, backend, frontend |

### Repo GitHub

```
https://github.com/tuananh-din/otechwiki.git
```

---

## 📁 Cấu trúc dự án hiện tại

### Backend (`backend/app/`)

| File | Chức năng |
|------|-----------|
| `main.py` | FastAPI app entry point |
| `api/auth.py` | JWT authentication, login |
| `api/documents.py` | CRUD documents, bulk delete, ingest, import |
| `api/search.py` | Search endpoint, AI synthesis |
| `core/config.py` | App config from .env |
| `core/database.py` | PostgreSQL async connection |
| `core/security.py` | JWT token, password hashing |
| `models/document.py` | SQLAlchemy models: Document, Chunk, Product, ProductAlias |
| `models/user.py` | User model |
| `schemas/schemas.py` | Pydantic schemas (request/response) |
| `services/ingest.py` | Web page ingestion (fetch + extract + chunk + embed) |
| `services/discovery.py` | Auto-discover sub-pages from a root URL |
| `services/search.py` | Vector similarity search + full-text |
| `services/rag.py` | RAG pipeline: retrieve → synthesize with GPT |
| `services/query_understanding.py` | Intent classification (comparison, recommendation, specs, etc.) |
| `services/follow_up.py` | Rule-based follow-up question generation |
| `services/embeddings.py` | OpenAI embeddings wrapper |
| `services/cleaner.py` | HTML boilerplate removal (30+ patterns) |
| `services/chunker_v2.py` | Heading-aware text chunking |
| `services/dedup.py` | URL/block/chunk deduplication |
| `services/mapper_v2.py` | Multi-source product mapping with aliases |
| `services/product_mapper.py` | Product name extraction from content |
| `services/import_jobs.py` | Background async import with progress tracking |
| `services/autocomplete.py` | Search autocomplete suggestions |
| `services/seed_autocomplete.py` | Seed autocomplete from existing data |

### Frontend (`frontend/src/`)

| File | Chức năng |
|------|-----------|
| `app/page.tsx` | Homepage / landing |
| `app/search/page.tsx` | AI search page (main feature) |
| `app/documents/page.tsx` | Document list + bulk delete |
| `app/documents/[id]/page.tsx` | Document detail view |
| `app/products/page.tsx` | Product catalog |
| `app/products/[slug]/page.tsx` | Product detail |
| `app/recent/page.tsx` | Recently viewed |
| `app/login/page.tsx` | Login page |
| `app/admin/page.tsx` | Admin dashboard |
| `app/admin/data-sources/page.tsx` | Data source management + import |
| `app/admin/cleaning-dashboard/page.tsx` | Content cleaning monitor |
| `app/admin/product-mapping/page.tsx` | Product mapping config |
| `app/admin/autocomplete-config/page.tsx` | Autocomplete configuration |
| `app/admin/analytics/page.tsx` | Usage analytics |
| `components/AppLayout.tsx` | Shared layout (sidebar, header) |
| `lib/api.ts` | API client (axios) |

---

## 🕐 Lịch sử phát triển theo thứ tự

### Phase 1: Foundation (Commit `f9cfed2` → `41a059e`)

**Mục tiêu:** Xây dựng nền tảng ứng dụng.

- ✅ Khởi tạo project
- ✅ Backend FastAPI + PostgreSQL pgvector
- ✅ Frontend Next.js
- ✅ Docker Compose (3 services: db, backend, frontend)
- ✅ Dockerfiles cho backend (Python 3.11-slim) và frontend (Node 20-alpine, multi-stage build)
- ✅ JWT Authentication (login, register)
- ✅ Document CRUD (upload, list, view, delete)
- ✅ Web page ingestion (fetch URL → extract text → chunk → embed → store)
- ✅ Vector similarity search

### Phase 2: Bug Fixes & Config (Commit `48893ec` → `26f3748`)

- ✅ Fix frontend port 3000 → 3001 (tránh conflict)
- ✅ Fix CORS origins cho cross-origin requests
- ✅ Fix API URL build-arg cho frontend Docker
- ✅ Thêm admin password reset script (`reset_admin.py`)
- ✅ CORS cho phép tất cả origins (dev mode)
- ✅ Cấu hình Cloudflare Tunnel cho public access
- ✅ Thêm dependency `markitdown`

### Phase 3: SaaS UI Redesign (Commit `77b7c94`)

**Mục tiêu:** Chuyển UI từ basic → professional SaaS.

- ✅ **Design System:** Glassmorphism, backdrop-blur, semi-transparent cards
- ✅ **Color Palette:** Blue-based (#0ea5e9 primary), dark background
- ✅ **Typography:** Poppins (headings) + Inter (body) từ Google Fonts
- ✅ **Icons:** Chuyển sang Lucide React SVG icons
- ✅ **Layout:** Responsive sidebar, mobile hamburger menu
- ✅ **Components:** Cards, badges, search bars với glassmorphism style

### Phase 4: Enhanced Web Crawler (Commit `ea07da3` — phần 1)

**Mục tiêu:** Crawl sâu hơn, import nhanh hơn.

- ✅ Tăng page limit 60 → 200
- ✅ Thêm Chrome User-Agent header (bypass 403 blocks)
- ✅ **Discovery service** (`discovery.py`): auto-discover sub-pages từ root URL
- ✅ **Background import** (`import_jobs.py`): async import với progress tracking
- ✅ API endpoints: `POST /admin/start-import`, `GET /admin/import-job/{id}`
- ✅ Frontend: progress bar (polling 2s), select-all toggle, re-import badge

### Phase 5: Ingest Pipeline V2 (Commit `ea07da3` — phần 2)

**Mục tiêu:** Cải thiện chất lượng data ingestion.

- ✅ **Schema migration:** Thêm `raw_text`, `cleaned_text`, `page_type`, `is_searchable`, `dedup_hash`, bảng `product_aliases`
- ✅ **Cleaner** (`cleaner.py`): BS4 boilerplate removal, 30+ pattern (ratings, colors, share buttons, footers)
- ✅ **Chunker V2** (`chunker_v2.py`): Heading-aware chunking, tách theo section
- ✅ **Dedup** (`dedup.py`): URL-level, block-level, chunk-level deduplication
- ✅ **Mapper V2** (`mapper_v2.py`): Multi-source confidence mapping với product aliases
- ✅ **Search update:** Dùng `cleaned_content` + `is_searchable` filter

### Phase 6: AI Search Features (Commit `ea07da3` — phần 3)

**Mục tiêu:** Search thông minh hơn với AI.

- ✅ **Intent Classification** (`query_understanding.py`): Phân loại query thành comparison, recommendation, specs, warranty, troubleshooting, price, general
- ✅ **AI Synthesis** (`rag.py`): Structured prompts cho comparison table, recommendation list, specs extraction
- ✅ **Follow-up Questions** (`follow_up.py`): Rule-based templates theo intent + product, zero token cost
- ✅ **Multi-query retrieval:** Cho policy/troubleshooting/specs intents (fix bug single query match sai page)

### Phase 7: Document Management (Commit `ea07da3` — phần 4)

- ✅ **Single delete:** `DELETE /api/documents/{id}`
- ✅ **Bulk delete:** `POST /api/documents/bulk-delete`
- ✅ **Duplicate prevention:** 409 trên ingest-web duplicate URL, 409 trên upload duplicate title
- ✅ Frontend: checkbox multi-select, select all, bulk delete confirm dialog
- ✅ DB CASCADE: chunks + product links tự cleanup

---

## 🐛 Các bug đã fix (quan trọng)

### Bug 1: Frontend gọi API sai URL
- **Vấn đề:** `docker-compose.yml` có `NEXT_PUBLIC_API_URL` trỏ Cloudflare tunnel thay vì `localhost:8000`
- **Hậu quả:** Frontend gọi backend cũ, không có features mới
- **Fix:** Sửa thành `http://localhost:8000`

### Bug 2: Search bị hỏng sau V2 pipeline reprocess
- **Vấn đề:** 3 bugs cùng lúc:
  1. `cleaner.py` missed boilerplate noise
  2. `chunker_v2.py` set `cleaned_content == content` (bao gồm `[Title]` prefix) → embedding sai
  3. RAG dùng single query → warranty query match product pages thay vì policy pages
- **Fix:** Sửa cả 3: thêm 30+ patterns cleaner, fix chunker dùng pure text, thêm multi-query retrieval

### Bug 3: Web crawler bị 403
- **Vấn đề:** Một số trang web block requests không có User-Agent
- **Fix:** Thêm Chrome User-Agent header vào `discovery.py` và `ingest.py`

---

## ⚙️ Cấu hình quan trọng

### File `.env` backend (KHÔNG có trên GitHub)

```env
DATABASE_URL=postgresql+asyncpg://ks_admin:ks_secret_2024@db:5432/knowledge_search
SECRET_KEY=<random-secret-key>
OPENAI_API_KEY=sk-...
DEBUG=false
WEB_EXTRACTOR_URL=
```

> ⚠️ Khi chạy Docker: host DB phải là `db` (tên service). Khi chạy local: dùng `localhost`.

### Docker Compose ports

| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| Backend API | 8000 |
| Frontend | 3001 → 3000 (internal) |

---

## 📋 Những việc CÓ THỂ cần làm tiếp

> ⚠️ Đây là gợi ý, chưa implement.

- [ ] Product autocomplete integration hoàn chỉnh
- [ ] Product mapping UI hoàn thiện
- [ ] Analytics dashboard data thực
- [ ] Caching layer cho search results
- [ ] Rate limiting cho API
- [ ] WebSocket real-time import progress (thay polling)
- [ ] PDF/DOCX upload parsing cải thiện
- [ ] Multi-tenant support
- [ ] Deploy lên Linux server (guide có ở `docs/GUIDE-deploy-server.md`)

---

## 🔗 Tài liệu liên quan

| File | Nội dung |
|------|----------|
| `docs/GUIDE-deploy-server.md` | Hướng dẫn deploy lên Linux server |
| `backend/.env.example` | Template biến môi trường backend |
| `backend/init.sql` | SQL khởi tạo database schema |
| `backend/reprocess_all.py` | Script reprocess toàn bộ documents qua pipeline V2 |

---

*Cập nhật lần cuối: 2026-03-09*
