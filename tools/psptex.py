def unswizzle(d,wbytes,h):
    out=bytearray(len(d)); bw=wbytes//16; i=0
    for by in range(h//8):
        for bx in range(bw):
            for r in range(8):
                o=(by*8+r)*wbytes+bx*16; out[o:o+16]=d[i:i+16]; i+=16
    return out
def swizzle(d,wbytes,h):
    out=bytearray(len(d)); bw=wbytes//16; i=0
    for by in range(h//8):
        for bx in range(bw):
            for r in range(8):
                o=(by*8+r)*wbytes+bx*16; out[i:i+16]=d[o:o+16]; i+=16
    return out
def to4(d,w,h):
    from PIL import Image
    px=[]
    for b in d: px+=[(b&15)*17,(b>>4)*17]
    im=Image.new('L',(w,h)); im.putdata(px[:w*h]); return im
