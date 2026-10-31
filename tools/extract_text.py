import json, re, struct, sys
from collections import Counter
sys.path.insert(0, 'tools')
from charmap import table
T = set(table())
JP = re.compile('[ぁ-んァ-ヶ一-龠々〆①-⑳㍉㌶㌃]')

def dec(b):
    s = []; i = 0
    while i < len(b):
        c = b[i]
        if c == 0: return ''.join(s), i
        if 0x20 <= c < 0x7f: s.append(chr(c)); i += 1; continue
        if i + 1 < len(b) and ((c << 8) | b[i + 1]) in T:
            s.append(bytes(b[i:i + 2]).decode('cp932', 'replace')); i += 2; continue
        return None, i
    return None, i

def stage():
    res = json.load(open('work/scan.json', encoding='utf-8'))
    out = []
    for k, v in sorted(res.items()):
        d = open('work/link/%s.bin' % k, 'rb').read()
        if d[:4].hex() not in ('00030000', '14000000', '80020000'): continue
        base = Counter(a % 64 for a, b, t in v).most_common(1)[0][0]
        offs = [a for a, b, t in v if a % 64 == base]
        lo = max(base, min(offs) - 64 * 120); hi = min(len(d) - 64, max(offs) + 64 * 120)
        o = lo - (lo - base) % 64
        while o <= hi:
            s, n = dec(d[o:o + 64])
            if s and JP.search(s) and not any(d[o + n:o + 64]):
                out.append(dict(f=k, o=o, cap=63, jp=s))
            o += 64
    return out

def eboot():
    e = open('work/eboot/EBOOT.ELF', 'rb').read()
    L = [l.split('\t') for l in open('work/eboot_cand.txt', encoding='utf-8').read().splitlines()]
    out = []
    for a, n, t in L:
        a = int(a, 16)
        if a < 0x400000: continue
        s, ln = dec(e[a:a + 400])
        if not s: continue
        v = a - 0x54 + 0x8804000
        refs = [m.start() for m in re.finditer(re.escape(struct.pack('<I', v)), e) if m.start() % 4 == 0]
        cap = ((ln + 1 + 3) & ~3) - 1
        out.append(dict(o=a, cap=cap, len=ln, refs=refs, jp=s))
    return out

if __name__ == '__main__':
    st = stage(); json.dump(st, open('work/stage_slots.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('stage slots', len(st), 'unique', len({x['jp'] for x in st}))
    eb = eboot(); json.dump(eb, open('work/eboot_strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('eboot', len(eb), 'norefs', sum(1 for x in eb if not x['refs']), 'unique', len({x['jp'] for x in eb}))
