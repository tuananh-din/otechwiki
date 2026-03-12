import json
d = json.load(open("/app/knowledge/evals/eval_report.json"))
s = d["summary"]
print(f"avg_score={s['avg_score']}")
print(f"passed={s['passed']}")
print(f"partial={s['partial']}")
print(f"failed={s['failed']}")
print(f"errors={s['errors']}")
print(f"struct_hits={s['structured_hits']}")
for r in d["results"]:
    sc = r.get("structured_count", 0)
    print(f"{r['id']}|{r['status']}|{r['score']}|{sc}")
