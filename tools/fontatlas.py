"""Font atlas 00032 (12px) / 00033 (14px): 512 wide 4bpp linear, 4 x 1bpp planes; glyph k -> plane k%4, cell k//4."""
FONTS={'00032':(240,12),'00033':(0x142,14)}
OFF=0x30
def load(f):
    h,cs=FONTS[f]; d=bytearray(open('work/link/%s.bin'%f,'rb').read()); return d,h,cs
def get(d,f,k):
    h,cs=FONTS[f]; per=512//cs; p=k%4; c=k//4; x0=(c%per)*cs; y0=(c//per)*cs
    g=[]
    for y in range(cs):
        row=[]
        for x in range(cs):
            X=x0+x; b=d[OFF+(y0+y)*256+X//2]; v=(b>>4) if X&1 else (b&15)
            row.append((v>>p)&1)
        g.append(row)
    return g
def put(d,f,k,g):
    h,cs=FONTS[f]; per=512//cs; p=k%4; c=k//4; x0=(c%per)*cs; y0=(c//per)*cs
    for y in range(cs):
        for x in range(cs):
            X=x0+x; o=OFF+(y0+y)*256+X//2; sh=(4 if X&1 else 0)+p
            if g[y][x]: d[o]|=(1<<sh)
            else: d[o]&=~(1<<sh)&0xff
