import json
near_misses = []
with open("knowledge_base/strategies_log.jsonl") as f:
    for line in f:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("outcome", "").startswith("rejected") and "near-miss" in json.dumps(e).lower():
            near_misses.append(e["id"])
print(len(near_misses))
print(near_misses[-30:])
