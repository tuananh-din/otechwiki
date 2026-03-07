# Knowledge Search — Tra cứu kiến thức sản phẩm nội bộ

Web app nội bộ dành cho Customer Service, giúp tra cứu thông tin sản phẩm trong 10-20 giây.  
AI trả lời có citation, tuyệt đối không hallucination.

## Quick Start

### 1. Khởi động Database

```bash
cd knowledge-search
docker compose up -d
```

### 2. Khởi động Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Sửa .env: điền OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 3. Khởi động Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Đăng nhập

Truy cập `http://localhost:3000/login`
- Username: `admin`
- Password: `admin123`

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js 14 + TypeScript + Tailwind |
| Backend | Python FastAPI |
| Database | PostgreSQL + pgvector |
| Search | Hybrid (keyword + semantic + RRF) |
| AI | OpenAI GPT-4o-mini + text-embedding-3-small |
| Auth | JWT + bcrypt |

## API Endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| POST | /api/auth/login | Đăng nhập |
| GET | /api/auth/me | Thông tin user |
| POST | /api/search | Tìm kiếm hybrid |
| POST | /api/ask | AI trả lời (RAG) |
| GET | /api/products | Danh sách sản phẩm |
| GET | /api/documents | Danh sách tài liệu |
| POST | /api/admin/upload-pdf | Upload PDF (admin) |
| POST | /api/admin/ingest-web | Ingest web (admin) |
| GET | /api/admin/analytics | Analytics (admin) |
