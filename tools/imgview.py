"""python tools/imgview.py out.png KEY [KEY...] : originals (and previews if work/tex/prev/KEY.png) on grey, x2, with 16px grid ticks"""
import sys, os
from PIL import Image, ImageDraw
out = sys.argv[1]; keys = sys.argv[2:]; Z = int(os.environ.get('Z', 2))
rows = []
for k in keys:
    ims = [Image.open('work/tex/%s.png' % k)]
    if os.path.exists('work/tex/prev/%s.png' % k): ims.append(Image.open('work/tex/prev/%s.png' % k))
    rows.append(ims)
W = max(sum(i.width * Z + 8 for i in r) for r in rows); H = sum(max(i.height for i in r) * Z + 14 for r in rows)
sh = Image.new('RGB', (min(W, 2000), H), (110, 110, 120)); d = ImageDraw.Draw(sh); y = 0
for k, r in zip(keys, rows):
    d.text((0, y), k, fill=(255, 255, 0)); x = 0; y += 12
    for im in r:
        im2 = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
        bg = Image.new('RGB', im2.size, (110, 110, 120))
        for gx in range(0, im.width, 16): ImageDraw.Draw(bg).line([(gx * Z, 0), (gx * Z, 3)], fill=(255, 0, 0))
        for gy in range(0, im.height, 16): ImageDraw.Draw(bg).line([(0, gy * Z), (3, gy * Z)], fill=(255, 0, 0))
        bg.paste(im2, (0, 0), im2); sh.paste(bg, (x, y)); x += im2.width + 8
    y += max(i.height for i in r) * Z + 2
sh.save(out)
