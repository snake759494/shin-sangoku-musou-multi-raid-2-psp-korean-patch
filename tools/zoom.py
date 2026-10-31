"""python tools/zoom.py IMG x y w h out [Z] : zoom crop with 8px grid labels"""
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert('RGBA'); x, y, w, h = map(int, sys.argv[2:6]); out = sys.argv[6]; Z = int(sys.argv[7]) if len(sys.argv) > 7 else 4
c = im.crop((x, y, x + w, y + h)).resize((w * Z, h * Z), Image.NEAREST)
bg = Image.new('RGB', c.size, (40, 40, 60)); bg.paste(c, (0, 0), c); d = ImageDraw.Draw(bg)
for gx in range((x + 7) // 8 * 8, x + w, 8):
    d.line([((gx - x) * Z, 0), ((gx - x) * Z, h * Z)], fill=(255, 0, 0) if gx % 32 == 0 else (110, 40, 40))
    if gx % 16 == 0: d.text(((gx - x) * Z + 1, 0), str(gx), fill=(255, 255, 0))
for gy in range((y + 7) // 8 * 8, y + h, 8):
    d.line([(0, (gy - y) * Z), (w * Z, (gy - y) * Z)], fill=(255, 0, 0) if gy % 32 == 0 else (110, 40, 40))
    d.text((0, (gy - y) * Z + 1), str(gy), fill=(0, 255, 255))
bg.save(out)
