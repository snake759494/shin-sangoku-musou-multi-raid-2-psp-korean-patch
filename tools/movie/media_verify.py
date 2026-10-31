import subprocess,re
import imageio_ffmpeg

def decode_compare(source,patched):
    results=[]
    for path in (source,patched):
        r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-threads','1','-i',str(path),'-map','0:v:0','-f','null','-'],capture_output=True,text=True)
        lines=[line for line in r.stderr.splitlines() if line.strip()]
        assert r.returncode==0,(path,r.stderr)
        unexpected=[line for line in lines if 'Application provided invalid, non monotonically increasing dts to muxer' not in line]
        assert not unexpected,(path,unexpected)
        results.append(lines)
    # Several shipped movies themselves have a one-frame clock discontinuity.
    # Preserve those PTS values. Do not conceal new warnings as baseline quirks.
    assert len(results[1])<=len(results[0]),results
    return {'original_container_timing_warnings':len(results[0]),'patched_container_timing_warnings':len(results[1]),'new_decode_errors':0,'decode_clean':not results[1]}
