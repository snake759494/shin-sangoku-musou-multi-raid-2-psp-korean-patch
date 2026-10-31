"""Merge trans/parts/*.json into trans/eboot_ko.json / trans/stage_ko.json."""
import json, glob, os, re
tr = {}
for p in sorted(glob.glob('trans/parts/*.json')):
    b = os.path.basename(p)[:-5]
    src = json.load(open('work/tr_in/%s.json' % b, encoding='utf-8'))
    part = json.load(open(p, encoding='utf-8'))
    for x in src:
        ko = part.get(str(x['id']))
        if ko is None: print('missing', b, x['id']); continue
        tr[x['jp']] = ko.replace('기요모리', '키요모리')
eb = json.load(open('work/eboot_strings.json', encoding='utf-8'))
st = json.load(open('work/stage_slots.json', encoding='utf-8'))
E = {}
for x in eb:
    if re.match(r'^(仮|ダミー|テスト)', x['jp']): E[x['jp']] = '-'
    elif x['jp'] in tr: E[x['jp']] = tr[x['jp']]
S = {x['jp']: tr[x['jp']] for x in st if x['jp'] in tr}
json.dump(E, open('trans/eboot_ko.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(S, open('trans/stage_ko.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(tr), len(E), len(S))
