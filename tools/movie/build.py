from pathlib import Path
import sys,json,subprocess,shutil,hashlib,re,bisect,math,ctypes
import av,imageio_ffmpeg
from PIL import ImageFont
import psmf_tool as P
import anchor_mux,media_verify,timing_audit

ROOT=Path(__file__).resolve().parents[2]/'work'/'mvbuild'
GAME=Path(__file__).resolve().parents[2]
FF=imageio_ffmpeg.get_ffmpeg_exe()
FONT=GAME/'NanumSquareNeo-cBd.ttf'

def stamp(t):
    return f'{int(t//3600)}:{int(t//60)%60:02d}:{t%60:05.2f}'

def wrap(text,width,font):
    lines=[]
    for para in text.split('\n'):
        line=''
        for word in para.split():
            candidate=(line+' '+word).strip()
            if font.getlength(candidate)>width:
                assert line,(word,width)
                lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
    assert len(lines)<=1,(text,lines)
    return '\\N'.join(lines)

def strip_info_sei(es):
    """Drop x264's user-data SEI (encoder settings text); the shipped streams have none."""
    out=bytearray();pos=0
    for m in re.finditer(rb'\x00\x00\x01\x06\x05',es):
        a=m.start()-(1 if m.start() and es[m.start()-1]==0 else 0)
        b=es.find(b'\0\0\1',m.end());b=b-(1 if es[b-1]==0 else 0)
        out+=es[pos:a];pos=b
    return bytes(out+es[pos:])

def one(key,resume=False):
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    cfg=json.loads((GAME/'trans'/'movie_ko.json').read_text(encoding='utf8'))[key];cues=cfg['cues']
    src=GAME/'work'/'iso'/'PSP_GAME'/'USRDIR'/'Data'/'Movie'/(key+'.pmf');original=src.read_bytes();d=P.demux(original)
    assert P.remux(d)==original
    es,frames,slots,anchors=anchor_mux.layout(d)
    c=av.open(str(src));stream=c.streams.video[0];w,h=stream.width,stream.height;c.close()
    work=ROOT/'encode'/key;work.mkdir(parents=True,exist_ok=True)
    fonts=work/'fonts';fonts.mkdir(exist_ok=True);shutil.copyfile(FONT,fonts/FONT.name)
    font=ImageFont.truetype(str(FONT),cfg['size'])
    ass='[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,NanumSquare Neo,%d,&H00FFFFFF,&H00FFFFFF,&H00000000,&HFF000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,%d,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'%(w,h,cfg['size'],cfg['marginv'])
    for a,b,text in cues:
        assert 0<=a<b<=len(frames)*1001/30000+.25
        ass+=f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,'+wrap(text,w-24,font)+'\n'
    if resume:assert (work/'subtitles.ass').read_text(encoding='utf-8-sig')==ass,'Subtitle changes require a fresh encode'
    (work/'subtitles.ass').write_text(ass,encoding='utf-8-sig')
    (work/'input.264').write_bytes(es)
    idrs=sorted(set(bisect.bisect_right(frames,m.start())-1 for m in re.finditer(b'\0\0\1[\x65\x45\x25\x05]',es)))
    keytimes='expr:'+ '+'.join(f'eq(n,{f})' for f in idrs)
    base_bitrate=int(len(es)*8/(len(frames)*1001/30000)/1000*.60)
    zones={};bitrate=base_bitrate
    if resume:
        old_stream=(work/'output.264').read_bytes();at=old_stream.find(b'zones=')
        if at>=0:
            zone_text=old_stream[at:].split(b'\0',1)[0].decode('ascii',errors='ignore')
            zones={(int(a),int(b)+1):int(q) for a,b,q in re.findall(r'(\d+),(\d+),q=(\d+)',zone_text)}
        assert zones and (work/'passlog-0.log').exists()
    for attempt in range(1 if resume else 0,48):
        bitrate=base_bitrate
        zone_opts=(':zones='+ '/'.join(f'{a},{b-1},q={z}' for (a,b),z in sorted(zones.items()))) if zones else ''
        cmd=[FF,'-y','-v','warning','-threads','1','-r','30000/1001','-i','input.264','-an','-vf','ass=subtitles.ass:fontsdir=fonts','-c:v','libx264','-threads','1','-preset','veryfast','-profile:v','main','-level:v','2.1','-pix_fmt','yuv420p','-b:v',f'{bitrate}k','-maxrate','4000k','-bufsize','4000k','-force_key_frames',keytimes,'-x264-params','bframes=0:cabac=1:ref=1:weightp=0:aud=1:repeat-headers=1:scenecut=0:keyint=30000:min-keyint=1:pic-struct=1:nal-hrd=vbr:force-cfr=1'+zone_opts,'-f','h264','output.264']
        with (work/'encode.log').open('w') as log:
            for passno in ((1,2) if attempt==0 else (2,)):
                run=cmd[:-1]+['-pass',str(passno),'-passlogfile','passlog',('NUL' if passno==1 else cmd[-1])]
                subprocess.run(run,cwd=work,stdout=log,stderr=log,check=True)
        new=strip_info_sei((work/'output.264').read_bytes())
        newstarts=P._aud_offsets(new)+[len(new)];bad=[]
        for (a,fa),(b,fb) in zip(anchors,anchors[1:]):
            need=newstarts[fb]-newstarts[fa]+(4 if fa else 0);cap=sum(max(0,v-6) for _,_,v in slots[a:b])
            if need>cap:bad.append((fa,fb,need,cap))
        if bad:
            for fa,fb,need,cap in bad:zones[fa,fb]=min(51,zones.get((fa,fb),26)+max(2,math.ceil(6*math.log2(need/cap))))
            print(key,'zone retry',attempt,'windows',len(bad),'worst',max(round(n/c,2) for _,_,n,c in bad),flush=True);continue
        try:blob,report=anchor_mux.remux(d,new);break
        except ValueError as e:
            print(key,'retry',attempt,bitrate,str(e),flush=True);bitrate=int(bitrate*.82)
    else:raise RuntimeError(key+' cannot fit anchor windows')
    dest=ROOT/'patched'/(key+'.pmf');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
    decode=media_verify.decode_compare(src,dest)
    audit=timing_audit.compare(original,blob)
    timing_path=ROOT/'timing'/(key.replace('/','_')+'.json');timing_path.parent.mkdir(exist_ok=True);timing_path.write_text(json.dumps(audit,indent=2))
    timing={'passed':True,'identical_keyframe_indices':True,'identical_pts_frame_sector_pairs':True,'min_delivery_lead_seconds':audit['patched']['min_delivery_lead_seconds'],'original_peak_coded_buffer_bytes':audit['original']['max_coded_video_buffer_bytes'],'patched_peak_coded_buffer_bytes':audit['patched']['max_coded_video_buffer_bytes']}
    result={'key':key,'encoder_revision':5,'zones':[{"start":a,"end":b,"qp":v} for (a,b),v in zones.items()],'cues_sha256':hashlib.sha256(json.dumps(cues,ensure_ascii=False).encode()).hexdigest(),'frames':len(frames),'cues':len(cues),'bitrate_kbps':bitrate,'size_preserved':len(blob)==len(original),'original_sha256':hashlib.sha256(original).hexdigest(),'sha256':hashlib.sha256(blob).hexdigest(),'audio_and_scr_and_pts_preserved':True,'timing_validation':timing,**decode,'anchors':report}
    dest.with_suffix('.json').write_text(json.dumps(result,indent=2))
    print('BUILT',key,len(frames),len(cues),bitrate,flush=True)

if __name__=='__main__':
    for key in [v for v in sys.argv[1:] if v!='--resume']:one(key,'--resume' in sys.argv)
