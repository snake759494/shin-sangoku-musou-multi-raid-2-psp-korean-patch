"""Koei texture container used in LINKDATA:
 u32 count, u32 offsets[count] ; entry: u32 total, u32 0x10, u32 imgsize, u32 0 ;
 image header (0x20): u32 datasize, u16 w, u16 h, u8 log2w, u8 log2h, u8 bpp8(1)/bpp4(0), ... then pixels, then palette block
 (u32 size, u32 0x10, ..., then RGBA8888 x 256/16)."""
import struct
from PIL import Image

def entries(d):
    n = struct.unpack_from('<I', d)[0]
    if n == 0 or n > 4096: return []
    offs = struct.unpack_from('<%dI' % n, d, 4)
    return list(offs)

def parse(d, o):
    total, hs, imgsz, _ = struct.unpack_from('<4I', d, o)
    dsz, w, h = struct.unpack_from('<IHH', d, o + 0x10)
    lw, lh, b8 = d[o + 0x18], d[o + 0x19], d[o + 0x1a]
    pix = o + 0x20
    pal = o + imgsz + 0x20
    return dict(total=total, w=w, h=h, lw=lw, lh=lh, bpp=8 if b8 else 4, pix=pix, dsz=dsz, pal=pal)

def decode(d, o, swz=True):
    t = parse(d, o)
    bpp = t['bpp']; bw = (1 << t['lw']) if False else t['w']
    stride = t['dsz'] * 8 // bpp // t['h']   # pixels per row in buffer
    raw = d[t['pix']:t['pix'] + t['dsz']]
    if swz:
        from psptex import unswizzle
        wb = stride * bpp // 8
        raw = unswizzle(raw, wb, t['h'] - t['h'] % 8) + raw[wb * (t['h'] - t['h'] % 8):]
    n = 256 if bpp == 8 else 16
    pal = [struct.unpack_from('<4B', d, t['pal'] + 4 * i) for i in range(n)]
    px = []
    if bpp == 8: idx = raw
    else:
        idx = []
        for b in raw: idx += [b & 15, b >> 4]
    im = Image.new('RGBA', (stride, t['h']))
    im.putdata([tuple(pal[i][:3]) + (min(255, pal[i][3] * 2),) for i in idx[:stride * t['h']]])
    return im.crop((0, 0, t['w'], t['h'])), t
