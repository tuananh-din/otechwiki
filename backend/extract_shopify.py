"""Extract product prices from Shopify JSON API and update DB. Run inside backend container."""
import asyncio
import httpx
import re
import json
from app.core.database import async_session
from app.models.document import Product
from sqlalchemy import select, update


SHOP_DOMAIN = "https://roborock.com.vn"


def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", text.lower().strip())


def format_price(price_str: str) -> str:
    """Format Shopify price (e.g. '8990000') to display format ('8.990.000₫')."""
    try:
        price = int(price_str)
        formatted = f"{price:,}".replace(",", ".")
        return f"{formatted}₫"
    except (ValueError, TypeError):
        return price_str


async def fetch_shopify_catalog(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all products from Shopify public API."""
    url = f"{SHOP_DOMAIN}/products.json?limit=250"
    resp = await client.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json().get("products", [])


def match_db_to_shopify(db_product_name: str, shopify_catalog: list[dict]) -> dict | None:
    """Match a DB product to a Shopify product by title similarity."""
    db_norm = _normalize(db_product_name)

    # Strategy 1: Exact title match
    for sp in shopify_catalog:
        if _normalize(sp["title"]) == db_norm:
            return sp

    # Strategy 2: DB name contains Shopify title or vice versa
    for sp in shopify_catalog:
        sp_norm = _normalize(sp["title"])
        if sp_norm in db_norm or db_norm in sp_norm:
            return sp

    # Strategy 3: Match by short model name (e.g. "F25 Ultra" in both)
    db_without_brand = re.sub(r"^roborock\s*", "", db_norm, flags=re.IGNORECASE).strip()
    for sp in shopify_catalog:
        sp_without_brand = re.sub(r"^roborock\s*", "", _normalize(sp["title"]), flags=re.IGNORECASE).strip()
        if sp_without_brand == db_without_brand:
            return sp

    return None


async def run_extraction():
    """Fetch prices from Shopify API for all products and update DB."""

    # 1. Fetch Shopify catalog
    async with httpx.AsyncClient() as client:
        print("Fetching Shopify catalog...", flush=True)
        shopify_catalog = await fetch_shopify_catalog(client)
        print(f"  Found {len(shopify_catalog)} products in Shopify", flush=True)

    # 2. Get DB products
    async with async_session() as db:
        result = await db.execute(select(Product))
        products = result.scalars().all()

    total = len(products)
    print(f"\nMatching {total} DB products to Shopify...", flush=True)
    print("=" * 60, flush=True)

    updated = 0
    errors = 0
    error_names = []

    for i, product in enumerate(products):
        sp = match_db_to_shopify(product.name, shopify_catalog)

        if not sp:
            print(f"[{i+1}/{total}] MISS: {product.name}", flush=True)
            errors += 1
            error_names.append(product.name)
            continue

        variants = sp.get("variants", [])
        if not variants:
            print(f"[{i+1}/{total}] NO VARIANTS: {product.name}", flush=True)
            errors += 1
            error_names.append(product.name)
            continue

        raw_price = variants[0].get("price", "0")
        compare_price = variants[0].get("compare_at_price", "")
        display_price = format_price(raw_price)
        display_compare = format_price(compare_price) if compare_price else ""
        description = re.sub(r"<[^>]+>", "", sp.get("body_html", "")).strip()

        # Update product metadata — merge with existing
        async with async_session() as db:
            result = await db.execute(select(Product).where(Product.id == product.id))
            fresh_product = result.scalar_one()
            existing_meta = fresh_product.metadata_ or {}

            existing_meta["price"] = display_price
            existing_meta["price_raw"] = int(raw_price)
            if display_compare:
                existing_meta["original_price"] = display_compare
            existing_meta["shopify_handle"] = sp.get("handle")
            existing_meta["shopify_product_id"] = sp.get("id")

            await db.execute(
                update(Product)
                .where(Product.id == product.id)
                .values(
                    description=description if description else fresh_product.description,
                    metadata_=existing_meta,
                )
            )
            await db.commit()

        updated += 1
        print(
            f"[{i+1}/{total}] OK: {product.name} → {sp['title']} | {display_price}",
            flush=True,
        )

    print("=" * 60, flush=True)
    print(f"DONE: {updated} updated, {errors} unmatched, {total} total", flush=True)
    if error_names:
        print(f"\nUnmatched products:", flush=True)
        for name in error_names:
            print(f"  - {name}", flush=True)


if __name__ == "__main__":
    asyncio.run(run_extraction())
