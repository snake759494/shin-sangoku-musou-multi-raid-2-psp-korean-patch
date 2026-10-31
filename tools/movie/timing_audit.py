"""Conservative compressed-video delivery audit against shipped timestamps.

This is a packet-arrival/decode-deadline model, not real PSP hardware proof.
It checks the whole AU has arrived before its original PTS and compares
outstanding coded-video bytes using the original one-frame DTS offset.
"""
from pathlib import Path
import bisect,json,re,sys,hashlib
import psmf_tool as P


def inspect(data):
    d=P.demux(data);es=d.video_es();starts=P._aud_offsets(es)
    ends=starts[1:]+[len(es)];packets=[];anchors=[];pos=0;events=[]
    for si,sec in enumerate(d.sectors):
        bits=''.join(f'{v:08b}' for v in sec.pack[4:14])
        scr=int(bits[2:5]+bits[6:21]+bits[22:37],2)
        for q in sec.packets:
            if q.sid!=0xE0:continue
            if q.flags2&128:
                frame=bisect.bisect_left(starts,pos)
                anchors.append((frame,P._read_ts(q.raw,9),si))
            pos+=len(q.payload);packets.append((pos,scr));events.append((scr,0,len(q.payload)))
    offsets=[v[0] for v in packets];aidx=0;leads=[];prev=0
    for i,end in enumerate(ends):
        while aidx+1<len(anchors) and anchors[aidx+1][0]<=i:aidx+=1
        a,t,_=anchors[aidx];pts=t+(i-a)*3003
        arrival=packets[bisect.bisect_left(offsets,end)][1]
        leads.append((pts-arrival)/90000)
        events.append((pts-3003,1,-(end-prev)));prev=end
    level=peak=0
    for _,_,delta in sorted(events):
        level+=delta;peak=max(peak,level)
        assert level>=0,('coded buffer underflow',level)
    assert level==0
    idrs=sorted(set(bisect.bisect_right(starts,m.start())-1 for m in re.finditer(b'\0\0\1[\x65\x45\x25\x05]',es)))
    audio=b''.join(q.raw for sec in d.sectors for q in sec.packets if q.sid==0xBD)
    return {'frames':len(starts),'min_delivery_lead_seconds':round(min(leads),6),'max_coded_video_buffer_bytes':peak,'idrs':idrs,'anchors':anchors,'audio_pes_sha256':hashlib.sha256(audio).hexdigest()}


def compare(source,patched):
    a=inspect(source);b=inspect(patched)
    assert len(source)==len(patched)
    assert a['frames']==b['frames']
    assert a['idrs']==b['idrs'],('keyframes changed',a['idrs'],b['idrs'])
    assert a['anchors']==b['anchors'],'PTS values, associated frames or sector locations changed'
    assert a['audio_pes_sha256']==b['audio_pes_sha256']
    assert b['min_delivery_lead_seconds']>0
    assert b['max_coded_video_buffer_bytes']<=a['max_coded_video_buffer_bytes']+2048
    return {'original':a,'patched':b,'passed':True,'source_sha256':hashlib.sha256(source).hexdigest(),'patched_sha256':hashlib.sha256(patched).hexdigest()}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];out=root/'timing';out.mkdir(exist_ok=True)
    for key in sys.argv[1:]:
        result=compare((root/(key+'.pmf')).read_bytes(),(root/'patched'/(key+'.pmf')).read_bytes())
        p=out/(key.replace('/','_')+'.json');p.write_text(json.dumps(result,indent=2))
        print(key,'lead',result['patched']['min_delivery_lead_seconds'],'buffer',result['patched']['max_coded_video_buffer_bytes'],flush=True)
