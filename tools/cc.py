"""python tools/cc.py KEY x y w h [gap] : bboxes of glyph groups (index!=0) in area"""
import sys, json, numpy as np, cv2
sys.path.insert(0, 'tools'); import imgpatch
k = sys.argv[1]; x, y, w, h = map(int, sys.argv[2:6]); g = int(sys.argv[6]) if len(sys.argv) > 6 else 2
idx = {('%s_%02d' % (e['f'], e['k'])): e for e in json.load(open('work/tex/index.json'))}[k]
d = open('work/link/%s.bin' % idx['f'], 'rb').read()
t, s, i, p, r = imgpatch.load(d, idx['o'])
m = (i[y:y + h, x:x + w] != 0).astype(np.uint8)
m2 = cv2.dilate(m, np.ones((2 * g + 1, 2 * g + 1), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(m2)
for j in sorted(range(1, n), key=lambda j: (st[j][1] // 8, st[j][0])):
    a, b, c, e, area = st[j]
    print([int(a + x + g), int(b + y + g), int(c - 2 * g), int(e - 2 * g)], area)
