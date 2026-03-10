"""Full product data audit: compare DB vs Shopify API. Run inside backend container."""
import asyncio
import httpx
import re
import json
from datetime import datetime
from app.core.database import async_session
from app.models.document import Product
from sqlalchemy import select

SHOP_DOMAIN = "https://roborock.com.vn"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def format_price(price_str: str) -> str:
    try:
        price = int(price_str)
        return f"{price:,}".replace(",", ".") + "₫"
    except (ValueError, TypeError):
        return str(price_str)


def match_db_to_shopify(db_name: str, catalog: list[dict]) -> dict | None:
    db_norm = _normalize(db_name)
    # Exact
    for sp in catalog:
        if _normalize(sp["title"]) == db_norm:
            return sp
    # Contains
    for sp in catalog:
        sp_norm = _normalize(sp["title"])
        if sp_norm in db_norm or db_norm in sp_norm:
            return sp
    # Model name
    db_short = re.sub(r"^roborock\s*", "", db_norm).strip()
    for sp in catalog:
        sp_short = re.sub(r"^roborock\s*", "", _normalize(sp["title"])).strip()
        if sp_short == db_short:
            return sp
    # Fuzzy: remove spaces and compare
    db_nospace = re.sub(r"\s+", "", db_short)
    for sp in catalog:
        sp_short = re.sub(r"^roborock\s*", "", _normalize(sp["title"])).strip()
        sp_nospace = re.sub(r"\s+", "", sp_short)
        if sp_nospace == db_nospace:
            return sp
    return None


async def run_audit():
    # Fetch Shopify catalog
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SHOP_DOMAIN}/products.json?limit=250", timeout=30)
        resp.raise_for_status()
        shopify_catalog = resp.json().get("products", [])

    # Get DB products
    async with async_session() as db:
        result = await db.execute(
            select(Product).order_by(Product.name)
        )
        products = result.scalars().all()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append(f"PRODUCT DATA AUDIT REPORT")
    lines.append(f"Generated: {now}")
    lines.append(f"DB Products: {len(products)}")
    lines.append(f"Shopify Products: {len(shopify_catalog)}")
    lines.append("=" * 100)
    lines.append("")

    ok_count = 0
    mismatch_count = 0
    miss_count = 0

    for product in products:
        meta = product.metadata_ or {}
        db_price = meta.get("price", "N/A")
        db_price_raw = meta.get("price_raw", "N/A")
        shopify_handle = meta.get("shopify_handle", "N/A")

        sp = match_db_to_shopify(product.name, shopify_catalog)

        if not sp:
            status = "❌ MISS"
            shopify_price = "N/A"
            shopify_title = "NOT FOUND"
            shopify_handle_live = "N/A"
            miss_count += 1
        else:
            variants = sp.get("variants", [])
            raw = variants[0].get("price", "0") if variants else "0"
            shopify_price = format_price(raw)
            shopify_title = sp["title"]
            shopify_handle_live = sp["handle"]

            if str(db_price_raw) == str(raw):
                status = "✅ OK"
                ok_count += 1
            else:
                status = "⚠️ MISMATCH"
                mismatch_count += 1

        lines.append(f"[{status}] {product.name}")
        lines.append(f"  DB ID:           {product.id}")
        lines.append(f"  DB Price:        {db_price} (raw: {db_price_raw})")
        lines.append(f"  Shopify Match:   {shopify_title}")
        lines.append(f"  Shopify Handle:  {shopify_handle_live}")
        lines.append(f"  Shopify Price:   {shopify_price}")
        lines.append(f"  Description:     {(product.description or '')[:80]}...")
        lines.append(f"  Key Specs:       {json.dumps(meta.get('key_specs', {}), ensure_ascii=False)[:100]}")
        lines.append(f"  Key Features:    {json.dumps(meta.get('key_features', []), ensure_ascii=False)[:100]}")
        lines.append("")

    lines.append("=" * 100)
    lines.append(f"SUMMARY: {ok_count} OK | {mismatch_count} MISMATCH | {miss_count} MISS | {len(products)} TOTAL")
    lines.append("=" * 100)

    report = "\n".join(lines)

    # Write to file
    with open("/tmp/product_audit.txt", "w", encoding="utf-8") as f:
        f.write(report)

    print(report, flush=True)


if __name__ == "__main__":
    asyncio.run(run_audit())
