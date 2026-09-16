import json, collections
fams = collections.Counter()
for line in open('knowledge_base/strategies_index.jsonl'):
    d = json.loads(line)
    tags = d.get('tags', {})
    fam = tags.get('indicator_family')
    if isinstance(fam, list):
        for f in fam:
            fams[f] += 1
    elif isinstance(fam, str) and fam:
        fams[fam] += 1
print(len(fams), 'unique indicator families')
print(fams.most_common(20))
