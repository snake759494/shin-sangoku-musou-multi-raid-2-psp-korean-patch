"""Contact sheet per movie: one frame every STEP seconds (work/mv/sheet_<name>.jpg)."""
import av, sys, glob, os
from PIL import Image
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 4
for p in sorted(glob.glob('work/iso/PSP_GAME/USRDIR/Data/Movie/*.pmf')):
    n = os.path.basename(p)[:-4]
    c = av.open(p); s = c.streams.video[0]
    shots = []; nxt = 0; t = 0
    for i, f in enumerate(c.decode(s)):
        t = i * 1001 / 30000
        if t >= nxt: shots.append(f.to_image().resize((240, 136))); nxt += STEP
    c.close()
    cols = 6; rows = (len(shots) + cols - 1) // cols
    sh = Image.new('RGB', (cols * 240, rows * 136))
    for k, im in enumerate(shots): sh.paste(im, (k % cols * 240, k // cols * 136))
    sh.save('work/mv/sheet_%s.jpg' % n, quality=80)
    print(n, s.width, s.height, round(t, 1), flush=True)
