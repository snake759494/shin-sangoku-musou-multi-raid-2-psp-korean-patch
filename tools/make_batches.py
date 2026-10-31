"""Split all unique source strings into translation batches work/tr_in/Bxx.json."""
import json, os, re
eb = json.load(open('work/eboot_strings.json', encoding='utf-8'))
st = json.load(open('work/stage_slots.json', encoding='utf-8'))
items = {}   # jp -> dict
def add(jp, mx, ctx, src):
    if jp in items:
        items[jp]['max'] = min(items[jp]['max'], mx); return
    items[jp] = dict(jp=jp, max=mx, ctx=ctx, src=src)
pre = set()
for x in eb:
    if re.match(r'^(仮|ダミー|テスト)', x['jp']): pre.add(x['jp']); continue
    cap = x['cap']
    mx = cap if cap <= 23 else int(cap * 1.3)
    add(x['jp'], mx, 'E%06x' % x['o'], 'E')
for x in st:
    add(x['jp'], 63, 'S' + x['f'], 'S')
E = [v for v in items.values() if v['src'] == 'E']
S = [v for v in items.values() if v['src'] == 'S']
os.makedirs('work/tr_in', exist_ok=True)
def split(lst, prefix, target):
    out = []; cur = []; n = 0
    for v in lst:
        cur.append(v); n += len(v['jp'])
        if n >= target or len(cur) >= 1100: out.append(cur); cur = []; n = 0
    if cur:
        if out and sum(len(v['jp']) for v in cur) < 1500: out[-1] += cur
        else: out.append(cur)
    names = []
    for i, b in enumerate(out):
        name = '%s%02d' % (prefix, i)
        json.dump([dict(id=j, jp=v['jp'], max=v['max'], ctx=v['ctx']) for j, v in enumerate(b)],
                  open('work/tr_in/%s.json' % name, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        names.append((name, len(b), sum(len(v['jp']) for v in b)))
    return names
print(split(E, 'E', 8000))
print(split(S, 'S', 8000))
