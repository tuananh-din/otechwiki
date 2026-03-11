"""Run batch extraction for top products. Execute inside backend container."""
import asyncio
from app.core.database import async_session
from app.models.document import Product, document_products
from app.services.knowledge_extractor import batch_extract
from sqlalchemy import select, func


async def run():
    # Find top 15 products by document count
    async with async_session() as db:
        result = await db.execute(
            select(Product.id, Product.name, func.count(document_products.c.document_id).label("doc_count"))
            .outerjoin(document_products, document_products.c.product_id == Product.id)
            .group_by(Product.id, Product.name)
            .order_by(func.count(document_products.c.document_id).desc())
            .limit(15)
        )
        top_products = result.all()

    print(f"Top {len(top_products)} products to extract:", flush=True)
    for p in top_products:
        print(f"  #{p.id} {p.name} ({p.doc_count} docs)", flush=True)

    product_ids = [p.id for p in top_products]

    print(f"\nRunning extraction for {len(product_ids)} products...", flush=True)
    async with async_session() as db:
        results = await batch_extract(db, product_ids, ["specs", "pricing", "faq"])

    print(f"\n{'='*60}", flush=True)
    print("EXTRACTION RESULTS", flush=True)
    print(f"{'='*60}", flush=True)
    for r in results:
        pid = r["product_id"]
        if "error" in r:
            print(f"  #{pid}: ERROR — {r['error']}", flush=True)
            continue
        for ext_type, ext_result in r.get("extractions", {}).items():
            if "error" in ext_result:
                print(f"  #{pid} [{ext_type}]: ERROR — {ext_result['error']}", flush=True)
            else:
                output = ext_result.get("output_path", "")
                extra = ""
                if ext_type == "specs":
                    extra = f" ({ext_result.get('specs_count', 0)} specs, {ext_result.get('features_count', 0)} features)"
                elif ext_type == "faq":
                    extra = f" ({ext_result.get('faq_count', 0)} FAQ pairs)"
                elif ext_type == "pricing":
                    extra = f" ({ext_result.get('price', 'N/A')})"
                print(f"  #{pid} [{ext_type}]: ✓ {output}{extra}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())
