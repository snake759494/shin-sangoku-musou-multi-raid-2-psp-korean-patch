"""python -I tools/check_batch.py BATCH   -> validates trans/parts/BATCH.json against work/tr_in/BATCH.json"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
from charmap import table, KEEP_BELOW
KEEP = {bytes([c >> 8, c & 255]).decode('cp932') for c in table() if c < KEEP_BELOW}
KEEP.discard('\u3000')
TOK = re.compile(r'\{(?:R|[CP][0-9A-Z])\}')
FMT = re.compile(r'%[-0-9.]*[sdxXcu]')

def nbytes(s):
    s = TOK.sub('', s); n = 0
    for ch in s:
        if ch == '\n' or ord(ch) < 0x7f: n += 1
        else: n += 2
    return n + 2 * 0  # tokens counted separately

def width(line):
    line = TOK.sub('', line)
    return sum(0.5 if ord(c) < 0x7f else 1 for c in line)

def check(name):
    src = json.load(open('work/tr_in/%s.json' % name, encoding='utf-8'))
    out = json.load(open('trans/parts/%s.json' % name, encoding='utf-8'))
    errs = []
    for it in src:
        k = str(it['id']); jp = it['jp']
        if k not in out: errs.append('%s missing' % k); continue
        ko = out[k]
        if not isinstance(ko, str) or not ko.strip():
            errs.append('%s empty' % k); continue
        bad = [c for c in TOK.sub('', ko) if not (c == '\n' or 0x20 <= ord(c) < 0x7f or '\uac00' <= c <= '\ud7a3' or c in KEEP)]
        if bad: errs.append('%s bad chars %r' % (k, ''.join(sorted(set(bad))))); continue
        b = nbytes(ko) + 2 * len(TOK.findall(ko)) + sum(1 for t in TOK.findall(ko) if t != '{R}')
        if b > it['max']: errs.append('%s too long %d > %d : %s' % (k, b, it['max'], ko))
        if sorted(TOK.findall(ko)) != sorted(TOK.findall(jp)): errs.append('%s control tokens differ' % k)
        if FMT.findall(ko) != FMT.findall(jp): errs.append('%s format specifiers differ %s vs %s' % (k, FMT.findall(jp), FMT.findall(ko)))
        jl, kl = jp.split('\n'), ko.split('\n')
        if len(kl) > len(jl): errs.append('%s too many lines %d > %d' % (k, len(kl), len(jl)))
        elif len(jl) > 1:
            lim = max(width(l) for l in jl) + 0.5
            for l in kl:
                if width(l) > lim: errs.append('%s line too wide %.1f > %.1f : %s' % (k, width(l), lim, l))
    extra = set(out) - {str(it['id']) for it in src}
    if extra: errs.append('unknown ids %s' % sorted(extra)[:10])
    return errs

if __name__ == '__main__':
    e = check(sys.argv[1])
    print('\n'.join(e[:80]))
    print('ERRORS: %d' % len(e))
