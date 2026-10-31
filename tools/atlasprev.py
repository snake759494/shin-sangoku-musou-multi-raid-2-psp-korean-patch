"""Preview a multi-CLUT texture with palettes recovered from PPSSPP dumps.
python tools/atlasprev.py KEY DUMPPREFIX out.png"""
import sys, glob, json, numpy as np
from PIL import Image
sys.path.insert(0, 'tools'); import imgpatch
k, pre, out = sys.argv[1:4]
e = {('%s_%02d' % (x['f'], x['k'])): x for x in json.load(open('work/tex/index.json'))}[k]
d = bytearray(open('work/link/%s.bin' % e['f'], 'rb').read())
t, s, i0, p, r = imgpatch.load(bytes(d), e['o'])
spec = json.load(open('trans/images.json', encoding='utf-8'))
imgpatch.apply(d, e['o'], spec[k])
t, s, i1, p, r = imgpatch.load(bytes(d), e['o'])
H, W = t['h'], t['w']; i0 = i0[:H, :W]; i1 = i1[:H, :W]
dumps = [np.asarray(Image.open(f).convert('RGBA'))[:H, :W].astype(float) for f in sorted(glob.glob('work/ppsspp/memstick/PSP/TEXTURES/ULJM05637/new/%s*.png' % pre))]
pals = []
for a in dumps:
    pal = np.zeros((256, 4))
    for v in np.unique(i0):
        m = i0 == v; pal[v] = np.median(a[m], 0)
    pals.append(pal)
outs = []
for idx in (i0, i1):
    img = np.zeros((H, W, 4))
    for by in range(0, H, 8):
        for bx in range(0, W, 8):
            sc = [a[by:by + 8, bx:bx + 8, 3].sum() for a in dumps]
            kk = int(np.argmax(sc))
            img[by:by + 8, bx:bx + 8] = pals[kk][idx[by:by + 8, bx:bx + 8]]
    outs.append(Image.fromarray(img.astype(np.uint8), 'RGBA'))
Z = 2
sh = Image.new('RGB', (W * Z, H * Z * 2 + 6), (40, 40, 60))
for n, im in enumerate(outs):
    im = im.resize((W * Z, H * Z), Image.NEAREST); sh.paste(im, (0, n * (H * Z + 6)), im)
sh.save(out)
