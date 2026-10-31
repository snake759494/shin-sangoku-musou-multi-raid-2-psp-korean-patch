import json, struct, sys
sys.path.insert(0, 'tools')
from textcodec import decode, JP
e = open('work/eboot/EBOOT.ELF', 'rb').read()
VB = 0x8804000 - 0x54
lo, hi = VB + 0x400000, VB + len(e)
refs = {}
for p in range(0x54, len(e) - 3, 4):
    w = struct.unpack_from('<I', e, p)[0]
    if lo <= w < hi:
        refs.setdefault(w - VB, []).append(p)
out = []
for o in sorted(refs):
    if e[o - 1] != 0: continue
    s, ln = decode(e, o)
    if not s or not JP.search(s): continue
    # capacity: up to next non-zero byte that is 4-aligned or the original NUL padding
    z = o + ln
    while z < len(e) and e[z] == 0 and (z + 1) % 4: z += 1
    out.append(dict(o=o, cap=z - o, len=ln, refs=refs[o], jp=s))
json.dump(out, open('work/eboot_strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(out), len({x['jp'] for x in out}), sum(len(x['jp']) for x in out))
print(sum(1 for x in out if '\n' in x['jp']), sum(1 for x in out if '{' in x['jp']))
