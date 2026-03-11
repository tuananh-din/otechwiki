"""Eval runner: tests RAG responses against eval_questions.json."""
import asyncio
import json
from app.core.database import async_session
from app.services.rag import ask_with_rag
from app.services.manifest import KNOWLEDGE_ROOT


async def run_eval():
    eval_path = KNOWLEDGE_ROOT / "evals" / "eval_questions.json"
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    questions = eval_data["questions"]
    results = []

    # Test a subset for speed
    test_ids = ["price_f25", "price_f25_ace_pro", "spec_qrevo_curv", "warranty_policy", "feature_saros_z70"]
    test_questions = [q for q in questions if q["id"] in test_ids]

    print(f"Running eval for {len(test_questions)} questions...\n", flush=True)

    async with async_session() as db:
        for q in test_questions:
            print(f"━━━ Q: {q['query']} ━━━", flush=True)
            try:
                result = await ask_with_rag(db, q["query"])
                answer = result.get("answer", "")[:300]
                structured = result.get("structured_sources", [])
                no_result = result.get("no_result", False)

                # Check expected content
                checks = []
                if "expected_answer_contains" in q:
                    for expected in q["expected_answer_contains"]:
                        found = expected.lower() in answer.lower()
                        checks.append(f"  {'✓' if found else '✕'} Contains '{expected}': {found}")
                if "must_not_contain" in q:
                    for bad in q["must_not_contain"]:
                        not_found = bad.lower() not in answer.lower()
                        checks.append(f"  {'✓' if not_found else '✕'} NOT contain '{bad}': {not_found}")

                print(f"  Structured sources: {len(structured)}", flush=True)
                for s in structured:
                    print(f"    → {s['type']}: {s['product']} ({s['intent']})", flush=True)
                print(f"  Answer preview: {answer[:150]}...", flush=True)
                for c in checks:
                    print(c, flush=True)
                print(f"  No result: {no_result}", flush=True)
                print(flush=True)

                results.append({"id": q["id"], "structured_count": len(structured), "no_result": no_result, "checks": checks})
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                results.append({"id": q["id"], "error": str(e)})
                print(flush=True)

    # Summary
    total = len(results)
    with_structured = sum(1 for r in results if r.get("structured_count", 0) > 0)
    errors = sum(1 for r in results if "error" in r)
    print(f"\n{'='*60}", flush=True)
    print(f"EVAL SUMMARY: {total} questions", flush=True)
    print(f"  Structured data injected: {with_structured}/{total}", flush=True)
    print(f"  Errors: {errors}/{total}", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    asyncio.run(run_eval())
