"""Find frames with caption-like text in the bottom band (bright thin strokes next to dark)."""
import av, sys, glob, os, json
import numpy as np
res = {}
for p in sorted(glob.glob('work/iso/PSP_GAME/USRDIR/Data/Movie/*.pmf')):
    n = os.path.basename(p)[:-4]
    if n.startswith('staffroll'): continue
    c = av.open(p); hits = []
    for i, f in enumerate(c.decode(video=0)):
        if i % 5: continue
        a = f.to_ndarray(format='gray').astype(int)[200:268]
        br = a > 200
        dk = np.zeros_like(br); dk[:, 1:] |= a[:, :-1] < 70; dk[:, :-1] |= a[:, 1:] < 70
        score = int((br & dk).sum())
        hits.append(score)
    c.close()
    h = np.array(hits); res[n] = hits
    print(n, int((h > 60).sum()), len(h), int(h.max()), flush=True)
json.dump(res, open('work/mv/detect.json', 'w'))
