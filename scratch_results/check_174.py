import json
with open('knowledge_base/strategies_log.jsonl') as f:
    for line in f:
        e = json.loads(line)
        if e.get('id') == '2026-09-17-174':
            print(e.get('outcome'))
            print(e.get('rejection_reason'))
