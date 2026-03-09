"""Extract structured product data using GPT-4o-mini. Run inside backend container."""
import asyncio
import json
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.core.database import async_session
from app.models.document import Document, Product, document_products
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

EXTRACT_PROMPT = """Bạn là hệ thống trích xuất dữ liệu sản phẩm. Từ nội dung trang web sản phẩm dưới đây, hãy trích xuất thông tin có cấu trúc.

QUY TẮC:
1. CHỈ trích xuất thông tin CÓ TRONG văn bản. KHÔNG bịa.
2. Nếu không tìm thấy thông tin nào → để giá trị null.
3. Giá phải giữ nguyên định dạng gốc (VD: "14.990.000₫").
4. Thông số kỹ thuật: giữ nguyên đơn vị đo.

Trả về JSON theo format:
{
  "product_name": "tên đầy đủ sản phẩm",
  "price": "giá bán (string, giữ nguyên format VD: 14.990.000₫)",
  "original_price": "giá gốc nếu có",
  "category": "robot | handheld | accessory",
  "description": "mô tả ngắn 1-2 câu",
  "key_specs": {
    "lực hút": "giá trị",
    "pin": "giá trị",
    "thể tích hộp bụi": "giá trị",
    "thể tích nước": "giá trị",
    "kích thước": "giá trị",
    "trọng lượng": "giá trị",
    "công suất": "giá trị",
    "thời gian sạc": "giá trị",
    "thời gian hoạt động": "giá trị"
  },
  "key_features": ["tính năng 1", "tính năng 2"],
  "warranty": "thời gian bảo hành",
  "in_box": ["phụ kiện 1", "phụ kiện 2"]
}

Chỉ bao gồm các key_specs có giá trị thực tế. Bỏ qua key nào không có dữ liệu."""


async def extract_one(doc_id: int, title: str, text: str) -> dict | None:
    """Extract structured data from a single document."""
    truncated = text[:3000]  # GPT context limit
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT},
                {"role": "user", "content": f"TIÊU ĐỀ: {title}\n\nNỘI DUNG:\n{truncated}"},
            ],
            temperature=0.0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        print(f"  ERR extract {doc_id}: {e}", flush=True)
        return None


async def run_extraction():
    """Extract structured data for all product_detail documents."""
    async with async_session() as db:
        result = await db.execute(
            select(Document.id, Document.title, Document.cleaned_text)
            .where(Document.page_type == "product_detail")
            .where(Document.cleaned_text.isnot(None))
        )
        docs = [(r[0], r[1], r[2]) for r in result.all()]

    total = len(docs)
    print(f"Extracting structured data for {total} product pages...", flush=True)

    success = 0
    for i, (doc_id, title, text) in enumerate(docs):
        data = await extract_one(doc_id, title, text)
        if not data:
            print(f"[{i+1}/{total}] SKIP: {title[:50]}", flush=True)
            continue

        async with async_session() as db:
            # Update document metadata
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(metadata_=data)
            )

            # Update linked product's metadata
            dp_result = await db.execute(
                select(document_products.c.product_id)
                .where(document_products.c.document_id == doc_id)
            )
            product_ids = [r[0] for r in dp_result.all()]

            for pid in product_ids:
                product_meta = {
                    "price": data.get("price"),
                    "original_price": data.get("original_price"),
                    "key_specs": data.get("key_specs", {}),
                    "key_features": data.get("key_features", []),
                    "warranty": data.get("warranty"),
                    "in_box": data.get("in_box", []),
                }
                await db.execute(
                    update(Product)
                    .where(Product.id == pid)
                    .values(
                        description=data.get("description"),
                        metadata_=product_meta,
                    )
                )
            await db.commit()
            success += 1
            price = data.get("price", "N/A")
            print(f"[{i+1}/{total}] OK: {title[:45]} | {price}", flush=True)

    print(f"\n{'='*50}", flush=True)
    print(f"EXTRACTION COMPLETE: {success}/{total}", flush=True)


asyncio.run(run_extraction())
