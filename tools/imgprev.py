"""Preview trans/images.json ops for KEYs (or all) -> work/tex/prev/KEY.png"""
import sys, json, os
sys.path.insert(0, 'tools')
import imgpatch
os.makedirs('work/tex/prev', exist_ok=True)
spec = json.load(open('trans/images.json', encoding='utf-8'))
idx = {('%s_%02d' % (x['f'], x['k'])): x for x in json.load(open('work/tex/index.json'))}
keys = sys.argv[1:] or [k for k in spec if not k.startswith('_')]
for k in keys:
    x = idx[k]; d = bytearray(open('work/link/%s.bin' % x['f'], 'rb').read())
    imgpatch.apply(d, x['o'], spec[k], 'work/tex/prev/%s.png' % k)
print('ok', len(keys))
