"""Extract product prices from Shopify JSON API and update DB. Run inside backend container."""
import asyncio
import httpx
import re
import json
from app.core.database import async_session
from app.models.document import Product
from sqlalchemy import select, update


SHOP_DOMAIN = "https://roborock.com.vn"


def product_name_to_handles(name: str) -> list[str]:
    """Generate possible Shopify handles from a product name."""
    # "Roborock F25 Ace Pro" -> ["roborock-f25-ace-pro", "may-hut-bui-lau-nha-roborock-f25-ace-pro"]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    handles = [slug]
    # Also try with "may-hut-bui-lau-nha-" prefix (older products)
    without_brand = re.sub(r"^roborock-", "", slug)
    handles.append(f"may-hut-bui-lau-nha-roborock-{without_brand}")
    # Also try without "roborock-" prefix
    handles.append(without_brand)
    return handles


def format_price(price_str: str) -> str:
    """Format Shopify price (e.g. '8990000') to display format ('8.990.000₫')."""
    try:
        price = int(price_str)
        formatted = f"{price:,}".replace(",", ".")
        return f"{formatted}₫"
    except (ValueError, TypeError):
        return price_str


async def fetch_shopify_product(client: httpx.AsyncClient, handle: str) -> dict | None:
    """Fetch product data from Shopify JSON API."""
    url = f"{SHOP_DOMAIN}/products/{handle}.json"
    try:
        resp = await client.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("product")
    except Exception:
        pass
    return None


async def run_extraction():
    """Fetch prices from Shopify API for all products and update DB."""
    async with async_session() as db:
        result = await db.execute(select(Product))
        products = result.scalars().all()

    total = len(products)
    print(f"Fetching Shopify data for {total} products...", flush=True)
    print("=" * 60, flush=True)

    updated = 0
    errors = 0

    async with httpx.AsyncClient() as client:
        for i, product in enumerate(products):
            handles = product_name_to_handles(product.name)

            shopify_data = None
            used_handle = None
            for handle in handles:
                shopify_data = await fetch_shopify_product(client, handle)
                if shopify_data:
                    used_handle = handle
                    break

            if not shopify_data:
                print(f"[{i+1}/{total}] MISS: {product.name} (tried: {handles})", flush=True)
                errors += 1
                continue

            # Extract price from first variant
            variants = shopify_data.get("variants", [])
            if not variants:
                print(f"[{i+1}/{total}] NO VARIANTS: {product.name}", flush=True)
                errors += 1
                continue

            raw_price = variants[0].get("price", "0")
            compare_price = variants[0].get("compare_at_price", "")
            display_price = format_price(raw_price)
            display_compare = format_price(compare_price) if compare_price else ""
            description = shopify_data.get("body_html", "")
            # Strip HTML tags from description
            description = re.sub(r"<[^>]+>", "", description).strip()

            # Update product metadata — merge with existing
            async with async_session() as db:
                result = await db.execute(
                    select(Product).where(Product.id == product.id)
                )
                fresh_product = result.scalar_one()
                existing_meta = fresh_product.metadata_ or {}

                # Update price fields from Shopify (source of truth)
                existing_meta["price"] = display_price
                existing_meta["price_raw"] = int(raw_price)
                if display_compare:
                    existing_meta["original_price"] = display_compare
                existing_meta["shopify_handle"] = used_handle
                existing_meta["shopify_product_id"] = shopify_data.get("id")

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
                f"[{i+1}/{total}] OK: {product.name} | "
                f"{display_price} (handle: {used_handle})",
                flush=True,
            )

    print("=" * 60, flush=True)
    print(f"DONE: {updated} updated, {errors} errors, {total} total", flush=True)


if __name__ == "__main__":
    asyncio.run(run_extraction())
