"""Segment Japanese caption cues: work/mv/cues_<name>.json + crop sheet."""
import av, sys, json
import numpy as np
from PIL import Image, ImageDraw
name = sys.argv[1]; y0, y1 = 200, 250
c = av.open('work/iso/PSP_GAME/USRDIR/Data/Movie/%s.pmf' % name)
masks = []; imgs = {}
for i, f in enumerate(c.decode(video=0)):
    a = f.to_ndarray(format='gray').astype(int)
    b = a[y0:y1]
    br = b > 170
    dk = np.zeros_like(br)
    for s in (1, 2): dk[:, s:] |= b[:, :-s] < 90; dk[:, :-s] |= b[:, s:] < 90
    m = br & dk
    masks.append(m); imgs[i] = None
    if i % 1 == 0: imgs[i] = f.to_image().crop((0, y0 - 10, 480, y1 + 22))
c.close()
segs = []; cur = None
for i, m in enumerate(masks):
    on = m.sum() > 40
    if on and cur and (m & cur['m']).sum() > 0.35 * min(m.sum(), cur['m'].sum()):
        cur['e'] = i; cur['m'] = cur['m'] | m if m.sum() < 1.5 * cur['m'].sum() else m
    else:
        if cur and cur['e'] - cur['s'] >= 10: segs.append(cur)
        cur = dict(s=i, e=i, m=m) if on else None
if cur and cur['e'] - cur['s'] >= 10: segs.append(cur)
out = []
sheet = Image.new('RGB', (960, 80 * len(segs)))
for k, s in enumerate(segs):
    mid = (s['s'] + s['e']) // 2
    im = imgs[mid].resize((960, 144 * 960 // 960 * 0 + (y1 - y0 + 32) * 2))
    sheet.paste(im.crop((0, 0, 960, 80)), (0, 80 * k))
    ImageDraw.Draw(sheet).text((4, 80 * k + 2), str(k), fill=(255, 0, 0))
    out.append(dict(i=k, s=round(s['s'] * 1001 / 30000, 2), e=round((s['e'] + 1) * 1001 / 30000, 2)))
json.dump(out, open('work/mv/cues_%s.json' % name, 'w'), indent=0)
sheet.save('work/mv/cuesheet_%s.png' % name)
print(len(out)); print(out)
