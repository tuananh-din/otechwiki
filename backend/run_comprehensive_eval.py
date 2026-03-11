"""Comprehensive eval: runs ALL eval questions and produces scored benchmark.

Usage: docker exec knowledge_backend python3 run_comprehensive_eval.py
"""
import asyncio
import json
import time
from app.core.database import async_session
from app.services.rag import ask_with_rag
from app.services.manifest import KNOWLEDGE_ROOT, _write_json, _now_iso


async def run_comprehensive_eval():
    eval_path = KNOWLEDGE_ROOT / "evals" / "eval_questions.json"
    if not eval_path.exists():
        print("ERROR: eval_questions.json not found. Generating default set...")
        generate_eval_questions()

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    questions = eval_data["questions"]
    print(f"{'='*70}")
    print(f"COMPREHENSIVE EVAL — {len(questions)} questions")
    print(f"{'='*70}\n")

    results = []
    total_start = time.time()

    async with async_session() as db:
        for i, q in enumerate(questions, 1):
            qid = q["id"]
            query = q["query"]
            print(f"[{i}/{len(questions)}] {qid}: {query}", flush=True)

            start = time.time()
            try:
                result = await ask_with_rag(db, query)
                elapsed = time.time() - start
                answer = result.get("answer", "")
                structured = result.get("structured_sources", [])
                no_result = result.get("no_result", False)

                # Score checks
                pass_count = 0
                total_checks = 0
                check_details = []

                if "expected_answer_contains" in q:
                    for expected in q["expected_answer_contains"]:
                        total_checks += 1
                        found = expected.lower() in answer.lower()
                        if found:
                            pass_count += 1
                        check_details.append({
                            "type": "contains",
                            "value": expected,
                            "passed": found,
                        })

                if "must_not_contain" in q:
                    for bad in q["must_not_contain"]:
                        total_checks += 1
                        not_found = bad.lower() not in answer.lower()
                        if not_found:
                            pass_count += 1
                        check_details.append({
                            "type": "not_contains",
                            "value": bad,
                            "passed": not_found,
                        })

                if "expected_product" in q:
                    total_checks += 1
                    product_match = any(
                        q["expected_product"].lower() in s.get("product", "").lower()
                        for s in structured
                    )
                    if product_match:
                        pass_count += 1
                    check_details.append({
                        "type": "product_match",
                        "value": q["expected_product"],
                        "passed": product_match,
                    })

                score = (pass_count / total_checks * 100) if total_checks > 0 else 100
                status = "PASS" if score >= 80 else "PARTIAL" if score >= 50 else "FAIL"

                print(f"  → {status} ({score:.0f}%) | structured={len(structured)} | {elapsed:.1f}s", flush=True)
                for cd in check_details:
                    mark = "✓" if cd["passed"] else "✕"
                    print(f"    {mark} {cd['type']}: {cd['value']}", flush=True)
                print(flush=True)

                results.append({
                    "id": qid,
                    "query": query,
                    "status": status,
                    "score": score,
                    "structured_count": len(structured),
                    "structured_sources": [
                        {"type": s.get("type"), "product": s.get("product"), "intent": s.get("intent")}
                        for s in structured
                    ],
                    "no_result": no_result,
                    "elapsed_s": round(elapsed, 2),
                    "checks": check_details,
                    "answer_preview": answer[:200],
                })

            except Exception as e:
                elapsed = time.time() - start
                print(f"  → ERROR: {e} | {elapsed:.1f}s\n", flush=True)
                results.append({
                    "id": qid,
                    "query": query,
                    "status": "ERROR",
                    "score": 0,
                    "error": str(e),
                    "elapsed_s": round(elapsed, 2),
                })

    total_elapsed = time.time() - total_start

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    with_struct = sum(1 for r in results if r.get("structured_count", 0) > 0)
    avg_score = sum(r.get("score", 0) for r in results) / total if total > 0 else 0
    avg_time = sum(r.get("elapsed_s", 0) for r in results) / total if total > 0 else 0

    print(f"\n{'='*70}")
    print(f"EVAL REPORT")
    print(f"{'='*70}")
    print(f"  Total questions:    {total}")
    print(f"  ✓ Passed (≥80%):    {passed}")
    print(f"  ◐ Partial (50-79%): {partial}")
    print(f"  ✕ Failed (<50%):    {failed}")
    print(f"  ⚠ Errors:           {errors}")
    print(f"  Average score:      {avg_score:.1f}%")
    print(f"  Structured hits:    {with_struct}/{total}")
    print(f"  Avg response time:  {avg_time:.1f}s")
    print(f"  Total time:         {total_elapsed:.1f}s")
    print(f"{'='*70}\n")

    # Save report
    report = {
        "timestamp": _now_iso(),
        "summary": {
            "total": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "errors": errors,
            "avg_score": round(avg_score, 1),
            "structured_hits": with_struct,
            "avg_response_time_s": round(avg_time, 1),
            "total_time_s": round(total_elapsed, 1),
        },
        "results": results,
    }
    report_path = KNOWLEDGE_ROOT / "evals" / "eval_report.json"
    _write_json(report_path, report)
    print(f"Report saved to: {report_path}")


def generate_eval_questions():
    """Generate comprehensive eval questions if missing."""
    questions = {
        "version": "2.0",
        "questions": [
            # ─── Price questions ───
            {"id": "price_f25", "query": "Giá Roborock F25 bao nhiêu?",
             "expected_product": "Roborock F25",
             "expected_answer_contains": ["8,990,000", "F25"]},
            {"id": "price_f25_ace", "query": "Roborock F25 Ace giá bao nhiêu?",
             "expected_product": "Roborock F25 Ace",
             "expected_answer_contains": ["F25 Ace"]},
            {"id": "price_f25_ultra", "query": "Giá bán F25 Ultra?",
             "expected_product": "Roborock F25 Ultra",
             "expected_answer_contains": ["F25 Ultra"]},
            {"id": "price_saros_z70", "query": "Roborock Saros Z70 giá bao nhiêu tiền?",
             "expected_product": "Roborock Saros Z70",
             "expected_answer_contains": ["Saros Z70"]},
            {"id": "price_saros_10r", "query": "Giá Saros 10R?",
             "expected_product": "Roborock Saros 10R",
             "expected_answer_contains": ["Saros 10R"]},
            # ─── Spec questions ───
            {"id": "spec_f25_suction", "query": "Lực hút Roborock F25 là bao nhiêu Pa?",
             "expected_product": "Roborock F25",
             "expected_answer_contains": ["Pa", "F25"]},
            {"id": "spec_saros_z70_battery", "query": "Pin Roborock Saros Z70 dung lượng bao nhiêu?",
             "expected_product": "Roborock Saros Z70",
             "expected_answer_contains": ["Saros Z70"]},
            {"id": "spec_qrevo_curv", "query": "Roborock Qrevo Curv có gì nổi bật?",
             "expected_product": "Roborock Qrevo Curv",
             "expected_answer_contains": ["Qrevo Curv"]},
            {"id": "spec_saros_20_sonic", "query": "Thông số kỹ thuật Saros 20 Sonic?",
             "expected_product": "Roborock Saros 20 Sonic",
             "expected_answer_contains": ["Saros 20 Sonic"]},
            {"id": "spec_qrevo_curv2_flow", "query": "Tính năng Qrevo Curv 2 Flow?",
             "expected_product": "Roborock Qrevo Curv 2 Flow",
             "expected_answer_contains": ["Curv 2 Flow"]},
            # ─── Comparison questions ───
            {"id": "compare_f25_lineup", "query": "So sánh F25, F25 Ace, F25 Ultra?",
             "expected_answer_contains": ["F25"]},
            {"id": "compare_saros_qrevo", "query": "Saros Z70 khác gì Qrevo Curv?",
             "expected_answer_contains": ["Saros", "Qrevo"]},
            # ─── Feature questions ───
            {"id": "feature_flexi_pro", "query": "Roborock Flexi Pro có tính năng gì?",
             "expected_product": "Roborock Flexi Pro",
             "expected_answer_contains": ["Flexi Pro"]},
            {"id": "feature_saros_10r", "query": "Saros 10R có những tính năng nào?",
             "expected_product": "Roborock Saros 10R",
             "expected_answer_contains": ["Saros 10R"]},
            # ─── General / policy ───
            {"id": "warranty_policy", "query": "Chính sách bảo hành Roborock như thế nào?",
             "expected_answer_contains": ["bảo hành"]},
            {"id": "recommendation_budget", "query": "Tư vấn robot hút bụi dưới 10 triệu?",
             "expected_answer_contains": ["Roborock"]},
            {"id": "recommendation_premium", "query": "Robot Roborock nào tốt nhất hiện tại?",
             "expected_answer_contains": ["Roborock"]},
            # ─── Edge cases ───
            {"id": "edge_nonexistent", "query": "Giá Roborock ABC123 XYZ?",
             "must_not_contain": ["8,990,000"]},
            {"id": "edge_vague", "query": "Robot hút bụi nào tốt?",
             "expected_answer_contains": ["Roborock"]},
            {"id": "edge_multilingual", "query": "What is the price of Roborock F25?",
             "expected_product": "Roborock F25",
             "expected_answer_contains": ["F25"]},
        ],
    }

    eval_path = KNOWLEDGE_ROOT / "evals" / "eval_questions.json"
    _write_json(eval_path, questions)
    print(f"Generated {len(questions['questions'])} eval questions at {eval_path}")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_eval())
