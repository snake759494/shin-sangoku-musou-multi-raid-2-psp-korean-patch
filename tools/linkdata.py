"""LINKDATA.BIN: u32 count, u32 sector offsets[count+1?]; FileSize.bin = sizes"""
import struct, os, sys
U='work/iso/PSP_GAME/USRDIR/'
def load():
    d=open(U+'LINKDATA.BIN','rb').read()
    n=struct.unpack_from('<I',d)[0]
    offs=struct.unpack_from('<%dI'%(n+1),d,4)
    sizes=struct.unpack('<%dI'%n,open(U+'FileSize.bin','rb').read())
    return d,n,offs,sizes
if __name__=='__main__':
    d,n,offs,sizes=load()
    os.makedirs('work/link',exist_ok=True)
    from collections import Counter
    c=Counter()
    for i in range(n):
        a=offs[i]*2048; b=offs[i+1]*2048 if i+1<len(offs) and offs[i+1] else len(d)
        blob=d[a:a+sizes[i]]
        assert sizes[i]<=b-a or i==n-1,(i,sizes[i],b-a)
        open('work/link/%05d.bin'%i,'wb').write(blob)
        c[blob[:4]]+=1
    print(offs[-1], len(d)//2048)
    for k,v in c.most_common(40): print(k,v)

def header():
    f = open(U + 'LINKDATA.BIN', 'rb'); n = struct.unpack('<I', f.read(4))[0]
    offs = struct.unpack('<%dI' % n, f.read(4 * n))
    sizes = struct.unpack('<%dI' % n, open(U + 'FileSize.bin', 'rb').read())
    return n, offs, sizes
