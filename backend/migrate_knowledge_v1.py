"""Knowledge Architecture V1 — Phase 1 Migration.

Runs inside the backend container:
  docker exec knowledge_backend python3 migrate_knowledge_v1.py

Actions:
1. Add new columns to documents and chunks tables
2. Set existing records to knowledge_layer='legacy', canonical_status='legacy'
3. Create knowledge/ directory tree on filesystem
4. Build initial inventory manifest
5. Seed eval_questions.json
"""
import asyncio
from app.core.database import engine, async_session
from app.services.manifest import create_folder_structure, build_inventory, KNOWLEDGE_ROOT, MANIFEST_DIR
from sqlalchemy import text
import json
from pathlib import Path


COLUMNS_DOCUMENTS = [
    ("knowledge_layer", "VARCHAR(20)", "'legacy'"),
    ("canonical_status", "VARCHAR(20)", "'legacy'"),
    ("knowledge_path", "VARCHAR(500)", "NULL"),
    ("product_code", "VARCHAR(100)", "NULL"),
    ("version_tag", "VARCHAR(50)", "NULL"),
]

COLUMNS_CHUNKS = [
    ("knowledge_layer", "VARCHAR(20)", "'legacy'"),
]


async def add_columns():
    """Add new columns via raw SQL (idempotent)."""
    async with engine.begin() as conn:
        for col_name, col_type, default in COLUMNS_DOCUMENTS:
            try:
                await conn.execute(text(
                    f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS "
                    f"{col_name} {col_type} DEFAULT {default}"
                ))
                print(f"  ✓ documents.{col_name} ({col_type})", flush=True)
            except Exception as e:
                print(f"  ⚠ documents.{col_name}: {e}", flush=True)

        for col_name, col_type, default in COLUMNS_CHUNKS:
            try:
                await conn.execute(text(
                    f"ALTER TABLE chunks ADD COLUMN IF NOT EXISTS "
                    f"{col_name} {col_type} DEFAULT {default}"
                ))
                print(f"  ✓ chunks.{col_name} ({col_type})", flush=True)
            except Exception as e:
                print(f"  ⚠ chunks.{col_name}: {e}", flush=True)


async def mark_legacy():
    """Set all existing records to legacy status."""
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "UPDATE documents SET knowledge_layer = 'legacy', canonical_status = 'legacy' "
            "WHERE knowledge_layer IS NULL OR knowledge_layer = 'legacy'"
        ))
        print(f"  ✓ Marked {result.rowcount} documents as legacy", flush=True)

        result = await conn.execute(text(
            "UPDATE chunks SET knowledge_layer = 'legacy' "
            "WHERE knowledge_layer IS NULL OR knowledge_layer = 'legacy'"
        ))
        print(f"  ✓ Marked {result.rowcount} chunks as legacy", flush=True)


def seed_eval_questions():
    """Create basic eval_questions.json for retrieval quality testing."""
    eval_path = KNOWLEDGE_ROOT / "evals" / "eval_questions.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)

    questions = {
        "version": "1.0",
        "description": "Bộ câu hỏi đánh giá chất lượng retrieval",
        "questions": [
            {
                "id": "price_f25",
                "query": "Giá bán của Roborock F25?",
                "intent": "price_lookup",
                "expected_product": "Roborock F25",
                "expected_answer_contains": ["8.990.000"],
                "must_not_contain": ["14.990.000", "F25 Ace Pro", "F25 Ultra"],
            },
            {
                "id": "price_f25_ace_pro",
                "query": "Roborock F25 Ace Pro giá bao nhiêu?",
                "intent": "price_lookup",
                "expected_product": "Roborock F25 Ace Pro",
                "expected_answer_contains": ["14.990.000"],
            },
            {
                "id": "feature_f25",
                "query": "Tính năng nổi bật của F25?",
                "intent": "feature_lookup",
                "expected_product": "Roborock F25",
                "must_not_contain": ["F25 Ace Pro", "F25 Ultra"],
            },
            {
                "id": "compare_f25_series",
                "query": "So sánh F25 và F25 Ace Pro?",
                "intent": "comparison",
                "expected_products": ["Roborock F25", "Roborock F25 Ace Pro"],
            },
            {
                "id": "spec_qrevo_curv",
                "query": "Thông số kỹ thuật Qrevo Curv?",
                "intent": "specifications",
                "expected_product": "Roborock Qrevo Curv",
                "must_not_contain": ["Qrevo Curv 2 Pro", "Qrevo Master"],
            },
            {
                "id": "price_s8_maxv",
                "query": "Giá Roborock S8 MaxV Ultra?",
                "intent": "price_lookup",
                "expected_product": "Roborock S8 Maxv Ultra",
            },
            {
                "id": "troubleshoot_error",
                "query": "Robot hút bụi Roborock bị lỗi E1 phải làm sao?",
                "intent": "troubleshooting",
                "expected_answer_type": "step_by_step",
            },
            {
                "id": "warranty_policy",
                "query": "Chính sách bảo hành Roborock?",
                "intent": "policy",
                "expected_answer_contains": ["bảo hành"],
            },
            {
                "id": "recommend_budget",
                "query": "Nên mua robot hút bụi nào dưới 10 triệu?",
                "intent": "model_recommendation",
                "expected_answer_type": "comparison_table",
            },
            {
                "id": "feature_saros_z70",
                "query": "Saros Z70 có tính năng gì đặc biệt?",
                "intent": "feature_lookup",
                "expected_product": "Roborock Saros Z70",
            },
            {
                "id": "compare_qrevo_vs_s8",
                "query": "So sánh Qrevo Curv và S8 MaxV Ultra?",
                "intent": "comparison",
                "expected_products": ["Roborock Qrevo Curv", "Roborock S8 Maxv Ultra"],
            },
            {
                "id": "dyad_pro_usage",
                "query": "Hướng dẫn sử dụng Dyad Pro Combo?",
                "intent": "how_to",
                "expected_product": "Roborock Dyad Pro Combo",
            },
            {
                "id": "price_flexi_pro",
                "query": "Máy hút bụi Flexi Pro giá bao nhiêu?",
                "intent": "price_lookup",
                "expected_product": "Roborock Flexi Pro",
            },
            {
                "id": "accessory_filter",
                "query": "Lõi lọc thay thế cho Qrevo Curv mua ở đâu?",
                "intent": "purchase",
                "expected_product": "Roborock Qrevo Curv",
            },
            {
                "id": "general_brand",
                "query": "Roborock là hãng nào? Có uy tín không?",
                "intent": "general",
                "expected_answer_type": "brand_info",
            },
            {
                "id": "spec_h60_ultra",
                "query": "Roborock H60 Ultra có lực hút bao nhiêu Pa?",
                "intent": "specifications",
                "expected_product": "Roborock H60 Ultra",
            },
            {
                "id": "compare_saros_10_vs_10r",
                "query": "Saros 10 và Saros 10R khác gì nhau?",
                "intent": "comparison",
                "expected_products": ["Roborock Saros 10", "Roborock Saros 10R"],
            },
            {
                "id": "feature_flexiarm",
                "query": "FlexiArm là gì?",
                "intent": "feature_lookup",
                "expected_answer_contains": ["FlexiArm"],
            },
            {
                "id": "price_saros_20_sonic",
                "query": "Giá Saros 20 Sonic?",
                "intent": "price_lookup",
                "expected_product": "Roborock Saros 20 Sonic",
            },
            {
                "id": "recommend_pet_hair",
                "query": "Nhà có thú cưng nên mua robot nào?",
                "intent": "model_recommendation",
                "expected_answer_type": "recommendation",
            },
        ],
    }

    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Seeded {len(questions['questions'])} eval questions → {eval_path}", flush=True)
    return len(questions["questions"])


async def run_migration():
    print("=" * 70, flush=True)
    print("Knowledge Architecture V1 — Phase 1 Migration", flush=True)
    print("=" * 70, flush=True)

    # 1. Add DB columns
    print("\n[1/5] Adding database columns...", flush=True)
    await add_columns()

    # 2. Mark existing data as legacy
    print("\n[2/5] Marking existing records as legacy...", flush=True)
    await mark_legacy()

    # 3. Create folder structure
    print("\n[3/5] Creating knowledge/ folder tree...", flush=True)
    created = create_folder_structure()
    print(f"  ✓ Created {len(created)} directories", flush=True)
    for d in created[:10]:
        print(f"    {d}", flush=True)
    if len(created) > 10:
        print(f"    ... and {len(created) - 10} more", flush=True)

    # 4. Build inventory
    print("\n[4/5] Building inventory manifest...", flush=True)
    inv = build_inventory()
    print(f"  ✓ Inventory: {inv['total_files']} files across {len(inv['layers'])} layers", flush=True)

    # 5. Seed eval questions
    print("\n[5/5] Seeding eval questions...", flush=True)
    seed_eval_questions()

    print("\n" + "=" * 70, flush=True)
    print("Phase 1 Migration COMPLETE", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(run_migration())
