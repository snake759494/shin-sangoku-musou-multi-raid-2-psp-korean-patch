import glob,re,struct,json,sys
e=open('work/eboot/EBOOT.ELF','rb').read()
TAB=set(struct.unpack_from('<3255I',e,0x8C5879C-0x8804000+0x54))
def runs(x,minjp=1):
    out=[];i=0;n=len(x)
    while i<n:
        j=i;s=[];bad=False
        while j<n:
            b=x[j]
            if 0x20<=b<0x7f: s.append(chr(b)); j+=1
            elif (0x81<=b<=0x9f or 0xe0<=b<=0xfc) and j+1<n:
                c=b<<8|x[j+1]
                if c not in TAB: break
                s.append(bytes(x[j:j+2]).decode('cp932','replace')); j+=2
            else: break
        t=''.join(s)
        if j>i and (j>=n or x[j]==0) and (i==0 or x[i-1]==0):
            jp=len(re.findall('[ぁ-んァ-ヶ一-龠々]',t))
            if jp>=minjp and jp*2>=len(t.replace(' ',''))*0.5: out.append((i,j,t))
        i=j+1 if j>i else i+1
    return out
if __name__=='__main__':
    res={}
    for f in sorted(glob.glob('work/link/*.bin')):
        x=open(f,'rb').read()
        r=runs(x,2)
        if len(r)>=2: res[f[-9:-4]]=r
    json.dump(res,open('work/scan.json','w'),ensure_ascii=False)
    allu=set()
    for k,v in res.items():
        for a,b,t in v: allu.add(t)
    print(len(res),len(allu),sum(len(t) for t in allu))
    from collections import Counter
    c=Counter(open('work/link/%s.bin'%k,'rb').read()[:4].hex() for k in res)
    print(c.most_common(20))
