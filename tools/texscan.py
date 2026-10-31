"""Scan every LINKDATA file for embedded ktex image headers at any 16-byte offset."""
import glob, os, struct, json, sys
sys.path.insert(0, 'tools')
import ktex
known = {(x['f'], x['o']) for x in json.load(open('work/tex/index.json'))}
out = []
for p in sorted(glob.glob('work/link/*.bin')):
    d = open(p, 'rb').read(); f = os.path.basename(p)[:5]
    for o in range(0, len(d) - 0x40, 16):
        if d[o + 4:o + 8] != b'\x10\0\0\0' or d[o + 12:o + 16] != b'\0\0\0\0': continue
        total, _, imgsz = struct.unpack_from('<3I', d, o)
        dsz, w, h = struct.unpack_from('<IHH', d, o + 0x10)
        lw, lh, b8 = d[o + 0x18], d[o + 0x19], d[o + 0x1a]
        if not (16 <= w <= 512 and 8 <= h <= 512 and lw < 10 and lh < 10 and (1 << lw) >= w and (1 << lh) >= h and b8 in (0, 1)): continue
        if not (0 < dsz <= imgsz <= total <= len(d) - o and imgsz == dsz + 0x20): continue
        if (f, o) in known: continue
        try: im, t = ktex.decode(d, o, swz=False)
        except Exception: continue
        if w < 48 or h < 16: continue
        im.save('work/tex/n_%s_%06x.png' % (f, o)); out.append(dict(f=f, o=o, w=w, h=h))
json.dump(out, open('work/tex/nested.json', 'w'))
print(len(out), len(set(x['f'] for x in out)))
