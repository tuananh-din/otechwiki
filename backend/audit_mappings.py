"""Audit document_products mapping accuracy. Run inside backend container."""
import asyncio
import json
from app.core.database import async_session
from app.models.document import Product, Document, document_products, ProductAlias
from sqlalchemy import select, func


async def run_audit():
    async with async_session() as db:
        # 1. Get all products
        products = (await db.execute(
            select(Product).order_by(Product.name)
        )).scalars().all()
        product_map = {p.id: p for p in products}

        # 2. Get all aliases
        aliases = (await db.execute(select(ProductAlias))).scalars().all()

        # 3. Get all document mappings
        mappings = (await db.execute(
            select(document_products)
        )).fetchall()

        # 4. Get all documents
        docs = (await db.execute(
            select(Document).order_by(Document.id)
        )).scalars().all()
        doc_map = {d.id: d for d in docs}

        # === REPORT ===
        print("=" * 100)
        print("DOCUMENT-PRODUCT MAPPING AUDIT")
        print(f"Products: {len(products)} | Documents: {len(docs)} | Mappings: {len(mappings)}")
        print("=" * 100)

        # Group mappings by product
        product_docs = {}
        for m in mappings:
            pid = m.product_id
            if pid not in product_docs:
                product_docs[pid] = []
            product_docs[pid].append(m)

        # Group mappings by document
        doc_products_map = {}
        for m in mappings:
            did = m.document_id
            if did not in doc_products_map:
                doc_products_map[did] = []
            doc_products_map[did].append(m)

        # A. Products with their mapped documents
        print("\n--- A. PRODUCT → DOCUMENTS MAPPING ---")
        for p in products:
            docs_for_product = product_docs.get(p.id, [])
            print(f"\n[Product #{p.id}] {p.name} ({len(docs_for_product)} docs)")
            for m in sorted(docs_for_product, key=lambda x: -x.confidence):
                doc = doc_map.get(m.document_id)
                if doc:
                    print(f"  doc={m.document_id} conf={m.confidence:.1f} by={m.matched_by:<10} "
                          f"type={doc.page_type or 'N/A':<20} title={doc.title[:60]}")

        # B. Documents mapped to MANY products (over-mapping)
        print("\n--- B. OVER-MAPPED DOCUMENTS (mapped to 3+ products) ---")
        for did, maps in sorted(doc_products_map.items()):
            if len(maps) >= 3:
                doc = doc_map.get(did)
                if doc:
                    print(f"\n[Doc #{did}] {doc.title[:80]} (type={doc.page_type})")
                    for m in sorted(maps, key=lambda x: -x.confidence):
                        p = product_map.get(m.product_id)
                        if p:
                            print(f"  → Product #{m.product_id} {p.name:<30} conf={m.confidence:.1f} by={m.matched_by}")

        # C. Aliases that could cause confusion
        print("\n--- C. AMBIGUOUS ALIASES (shared across products) ---")
        alias_groups = {}
        for a in aliases:
            key = a.alias.lower()
            if key not in alias_groups:
                alias_groups[key] = []
            alias_groups[key].append(a)

        for alias_text, group in sorted(alias_groups.items()):
            if len(group) >= 2:
                product_names = [product_map.get(a.product_id, Product()).name for a in group]
                print(f"  Alias '{alias_text}' → {', '.join(product_names)}")

        # D. F25 family deep dive
        print("\n--- D. F25 FAMILY DEEP DIVE ---")
        f25_products = [p for p in products if 'f25' in p.name.lower()]
        for p in f25_products:
            docs_for = product_docs.get(p.id, [])
            print(f"\n  [{p.name}] ({len(docs_for)} docs)")
            for m in sorted(docs_for, key=lambda x: -x.confidence):
                doc = doc_map.get(m.document_id)
                if doc:
                    print(f"    doc={m.document_id} conf={m.confidence:.1f} by={m.matched_by:<10} "
                          f"title={doc.title[:70]}")


if __name__ == "__main__":
    asyncio.run(run_audit())
