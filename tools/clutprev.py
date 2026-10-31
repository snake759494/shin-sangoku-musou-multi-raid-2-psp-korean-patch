"""python tools/clutprev.py KEY x y w h out : before/after crop using the op's CLUT, x2"""
import sys, json, numpy as np
sys.path.insert(0, 'tools'); import imgpatch
from PIL import Image
k = sys.argv[1]; x, y, w, h = map(int, sys.argv[2:6]); out = sys.argv[6]
e = {('%s_%02d' % (a['f'], a['k'])): a for a in json.load(open('work/tex/index.json'))}[k]
ops = json.load(open('trans/images.json', encoding='utf-8'))[k]
pal = np.array(json.load(open('trans/clut_%s.json' % ops[0]['clut_file']))['pals'][ops[0]['clut']])
d = bytearray(open('work/link/%s.bin' % e['f'], 'rb').read())
i0 = imgpatch.load(bytes(d), e['o'])[2]; imgpatch.apply(d, e['o'], ops); i1 = imgpatch.load(bytes(d), e['o'])[2]
sh = Image.new('RGB', (w * 4 + 8, h * 2), (70, 70, 90))
for n, i in enumerate((i0, i1)):
    im = Image.fromarray(pal[i][y:y + h, x:x + w].astype(np.uint8), 'RGBA').resize((w * 2, h * 2), Image.NEAREST)
    sh.paste(im, (n * (w * 2 + 8), 0), im)
sh.save(out)
