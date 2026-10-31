import sys
sys.path.insert(0, 'tools')
from fontatlas import load, put
from render import glyph
CFG = {'00032': ('work/fonts/Galmuri11.ttf', 12, 0), '00033': ('NanumSquareNeo-bRg.ttf', 14, 0)}

def patch(m):
    out = {}
    for f, (font, size, dy) in CFG.items():
        d, h, cs = load(f)
        for ch, (i, code) in m.items():
            put(d, f, i, glyph(ch, font, cs, size, dy=dy))
        out[f] = bytes(d)
    return out
