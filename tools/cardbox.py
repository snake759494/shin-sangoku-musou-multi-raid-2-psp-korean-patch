"""Measure white body text bbox on cards (bright pixels with dark outline nearby)."""
import numpy as np, json, sys
from PIL import Image
def body_box(key, y0=60):
    a = np.asarray(Image.open('work/tex/%s.png' % key).convert('RGB')).astype(int)
    br = a.min(-1) > 205
    dk = a.max(-1) < 80
    near = np.zeros_like(dk)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            near |= np.roll(np.roll(dk, dy, 0), dx, 1)
    m = br & near; m[:y0] = False; m[:, :252] = False
    rows = np.where(m.sum(1) >= 2)[0]; cols = np.where(m.sum(0) >= 2)[0]
    return [int(cols.min()), int(rows.min()), int(cols.max() - cols.min() + 1), int(rows.max() - rows.min() + 1)]
if __name__ == '__main__':
    for k in sys.argv[1:]: print(k, body_box(k))
