"""Dump every ktex image in work/link -> work/tex/<file>_<k>.png + work/tex/index.json."""
import os, glob, json, struct, sys
sys.path.insert(0, 'tools')
import ktex
os.makedirs('work/tex', exist_ok=True)
idx = []
for p in sorted(glob.glob('work/link/*.bin')):
    d = open(p, 'rb').read()
    if len(d) < 0x60: continue
    try: offs = ktex.entries(d)
    except struct.error: continue
    if not offs or any(o >= len(d) or o < 4 for o in offs): continue
    ok = []
    for k, o in enumerate(offs):
        try:
            t = ktex.parse(d, o)
            if not (8 <= t['w'] <= 1024 and 8 <= t['h'] <= 1024 and t['hs'] if False else 8 <= t['w'] <= 1024 and 8 <= t['h'] <= 1024): raise ValueError
            if struct.unpack_from('<I', d, o + 4)[0] != 0x10 or t['pal'] + 64 > len(d) or t['dsz'] <= 0: raise ValueError
            ok.append((k, o, t))
        except Exception: ok = None; break
    if not ok: continue
    f = os.path.basename(p)[:5]
    for k, o, t in ok:
        try: im, _ = ktex.decode(d, o, swz=False)
        except Exception as e: continue
        if t['w'] < 48 or t['h'] < 16: continue
        im.save('work/tex/%s_%02d.png' % (f, k))
        idx.append(dict(f=f, k=k, o=o, w=t['w'], h=t['h'], bpp=t['bpp']))
json.dump(idx, open('work/tex/index.json', 'w'))
print(len(idx), len(set(x['f'] for x in idx)))
