"""Print eval summary — just run inside container."""
import json
d = json.load(open("/app/knowledge/evals/eval_report.json"))
s = d["summary"]
print("=" * 60)
print("EVAL BENCHMARK RESULTS")
print("=" * 60)
for k, v in s.items():
    print(f"  {k}: {v}")
print()
for r in d["results"]:
    sid = r["id"]
    status = r["status"]
    score = r.get("score", 0)
    struct = r.get("structured_count", 0)
    print(f"  {sid:35s} {status:8s} {score:5.0f}%  struct={struct}")
print("=" * 60)
