with open('knowledge_base/strategies_index.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
line = lines[1809]
print('open', line.count('{'), 'close', line.count('}'))
print('quotes', line.count('"'))
import json
try:
    json.loads(line)
    print("PARSE OK")
except Exception as e:
    print("PARSE FAIL", repr(e))
