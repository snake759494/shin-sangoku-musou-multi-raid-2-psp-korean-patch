"""Rewrite Japanese wording inside LINKDATA ktex textures.

trans/images.json: {"FFFFF_KK": [op, ...]}  (texture = LINKDATA file FFFFF, entry KK)
op:
  {"erase": [x, y, w, h]}                  clear to transparent (or "inpaint": true -> fill from surroundings)
  {"text": "처음부터", "box": [x, y, w, h], "font": "brush"|"serif"|"gothic"|"pixel",
   "size": 20, "fill": "#rrggbb", "outline": "#rrggbb", "ow": 1, "glow": 0,
   "style_from": [x, y, w, h], "align": "c"|"l"|"r", "vertical": false, "lines": 1, "spacing": 0,
   "bold": 0, "erase": true}
  "style_from" samples fill/outline colours from the original pixels in that rectangle.
  A text op erases its own box first unless "erase": false.
Indices are re-quantised to the texture's own palette, so size and palette stay unchanged.
"""
import json, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import ktex

FONTS = {
    'brush': 'SeoulHangangEB.ttf',
    'serif': 'SeoulHangangB.ttf',
    'serifm': 'SeoulHangangM.ttf',
    'gothic': 'NanumSquareNeo-dEb.ttf',
    'gothicb': 'NanumSquareNeo-cBd.ttf',
    'gothicr': 'NanumSquareNeo-bRg.ttf',
    'pixel': 'work/fonts/Galmuri11.ttf',
    'pixelb': 'work/fonts/Galmuri11-Bold.ttf',
    'pixel9': 'work/fonts/Galmuri9.ttf',
    'pixel7': 'work/fonts/Galmuri7.ttf',
}

def load(d, o):
    t = ktex.parse(d, o)
    bpp = t['bpp']; h = t['h']
    stride = t['dsz'] * 8 // bpp // h
    raw = d[t['pix']:t['pix'] + t['dsz']]
    if bpp == 8: idx = np.frombuffer(raw, np.uint8).copy()
    else:
        b = np.frombuffer(raw, np.uint8)
        idx = np.empty(b.size * 2, np.uint8); idx[0::2] = b & 15; idx[1::2] = b >> 4
    idx = idx[:stride * h].reshape(h, stride)
    n = 256 if bpp == 8 else 16
    pal = np.frombuffer(d[t['pal']:t['pal'] + 4 * n], np.uint8).reshape(n, 4).copy()
    rgba = pal.astype(int).copy(); rgba[:, 3] = np.minimum(255, rgba[:, 3] * 2)
    return t, stride, idx, pal, rgba

def store(d, t, stride, idx):
    flat = idx.reshape(-1)
    if t['bpp'] == 8: raw = flat.astype(np.uint8).tobytes()
    else: raw = (flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes()
    assert len(raw) == t['dsz']
    d[t['pix']:t['pix'] + t['dsz']] = raw

def quantize(img, rgba):
    """img: HxWx4 float/uint8 -> nearest palette index (alpha weighted)."""
    a = img.reshape(-1, 4).astype(np.int32)
    p = rgba.astype(np.int32)
    out = np.empty(len(a), np.uint8)
    for s in range(0, len(a), 4096):
        q = a[s:s + 4096]
        # colour distance scaled by alpha; transparent pixels only care about alpha
        al = np.minimum(q[:, None, 3], p[None, :, 3]) / 255.0
        dc = ((q[:, None, :3] - p[None, :, :3]) ** 2).sum(-1) * al
        da = (q[:, None, 3] - p[None, :, 3]) ** 2 * 3
        out[s:s + 4096] = np.argmin(dc + da, 1)
    return out.reshape(img.shape[:2])

def sample_style(img, box):
    x, y, w, h = box
    reg = img[y:y + h, x:x + w].astype(int)
    a = reg[..., 3]
    solid = a > 200
    if solid.sum() < 4: return (255, 255, 255), (0, 0, 0)
    lum = reg[..., :3].sum(-1)
    m = solid
    # interior = solid pixels whose 4 neighbours are solid
    inner = m.copy()
    inner[1:] &= m[:-1]; inner[:-1] &= m[1:]; inner[:, 1:] &= m[:, :-1]; inner[:, :-1] &= m[:, 1:]
    edge = m & ~inner
    pick = lambda mask: tuple(int(v) for v in np.median(reg[mask][:, :3], 0)) if mask.sum() else (0, 0, 0)
    li, le = lum[inner].mean() if inner.sum() else 0, lum[edge].mean() if edge.sum() else 0
    # brighter of the two is usually the fill for light-on-dark captions
    fill, out = pick(inner), pick(edge)
    return fill, out

def hexc(c):
    if isinstance(c, str): c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c)

def render(op, W, H):
    """Return RGBA float layer (H, W, 4) of the text op."""
    font = ImageFont.truetype(FONTS[op.get('font', 'gothic')], op['size'])
    x, y, w, h = op['box']
    text = op['text']
    lines = text.split('\n')
    ow = op.get('ow', 1)
    sp = op.get('spacing', 0)
    S = 4  # supersample
    fontS = ImageFont.truetype(FONTS[op.get('font', 'gothic')], op['size'] * S)
    if op.get('vertical'):
        chars = [c for c in text if c != '\n']
        step = op.get('step', op['size'])
        canvas = Image.new('L', (w * S, h * S))
        dr = ImageDraw.Draw(canvas)
        tot = step * len(chars)
        y0 = (h - tot) // 2 if op.get('align', 'c') == 'c' else 0
        for i, c in enumerate(chars):
            bb = dr.textbbox((0, 0), c, font=fontS)
            dr.text(((w * S - (bb[2] - bb[0])) // 2 - bb[0], (y0 + i * step) * S - bb[1] + (step * S - (bb[3] - bb[1])) // 2), c, font=fontS, fill=255)
        mask = canvas
    else:
        lh = op.get('line_h', op['size'] + 2)
        canvas = Image.new('L', (w * S * 2, h * S * 2))
        dr = ImageDraw.Draw(canvas)
        widths = []
        for ln in lines:
            bb = dr.textbbox((0, 0), ln, font=fontS)
            widths.append(bb[2] - bb[0] + sp * S * max(0, len(ln) - 1))
        maxw = max(widths)
        sx = op.get('sx', 1.0)
        if maxw * sx > (w - 2 * ow) * S: sx = (w - 2 * ow) * S / maxw   # squeeze to fit
        tot = lh * len(lines)
        ty = (0 if op.get('valign') == 't' else (h - tot) // 2) + op.get('dy', 0)
        tmp = Image.new('L', (int(maxw) + 8 * S, tot * S + 8 * S))
        td = ImageDraw.Draw(tmp)
        asc = fontS.getmetrics()[0]
        for i, ln in enumerate(lines):
            lx = 0
            al = op.get('align', 'c')
            if al == 'c': lx = (maxw - widths[i]) / 2
            elif al == 'r': lx = maxw - widths[i]
            cy = i * lh * S + (lh * S - (fontS.getbbox('가')[3] + fontS.getbbox('가')[1])) // 2
            if sp:
                cx = lx
                for c in ln:
                    td.text((cx, cy), c, font=fontS, fill=255); cx += td.textlength(c, font=fontS) + sp * S
            else:
                td.text((lx, cy), ln, font=fontS, fill=255)
        nw = max(1, int(tmp.width * sx))
        tmp = tmp.resize((nw, tmp.height))
        mask = Image.new('L', (w * S, h * S))
        al = op.get('align', 'c')
        if al == 'c': px = (w * S - (maxw * sx)) / 2
        elif al == 'r': px = w * S - maxw * sx - ow * S
        else: px = ow * S
        mask.paste(tmp, (int(px + op.get('dx', 0) * S), ty * S))
    if op.get('italic'):
        k = op['italic']; mh = mask.height
        mask = mask.transform(mask.size, Image.AFFINE, (1, k, -k * mh / 2, 0, 1, 0), Image.BICUBIC)
    if op.get('bold'):
        mask = mask.filter(ImageFilter.MaxFilter(op['bold'] * 2 + 1))
    m = np.asarray(mask.resize((w, h), Image.LANCZOS)).astype(float) / 255
    fill = np.array(hexc(op['fill']), float)
    layer = np.zeros((H, W, 4))
    if ow > 0 or op.get('glow'):
        big = mask
        r = int(round(ow * S))
        if r: big = mask.filter(ImageFilter.MaxFilter(r * 2 + 1))
        if op.get('glow'): big = big.filter(ImageFilter.GaussianBlur(op['glow'] * S))
        o = np.asarray(big.resize((w, h), Image.LANCZOS)).astype(float) / 255
        if op.get('glow'): o = np.minimum(1, o * 1.8)
        oc = np.array(hexc(op['outline']), float)
        sub = layer[y:y + h, x:x + w]
        sub[..., :3] = oc; sub[..., 3] = o * 255
    sub = layer[y:y + h, x:x + w]
    a0 = sub[..., 3] / 255
    a = m + a0 * (1 - m)
    col = (fill * m[..., None] + sub[..., :3] * (a0 * (1 - m))[..., None]) / np.maximum(a, 1e-6)[..., None]
    sub[..., :3] = col; sub[..., 3] = a * 255
    if op.get('grad'):  # vertical gradient top->bottom colour for fill
        g2 = np.array(hexc(op['grad']), float)
        t = np.linspace(0, 1, h)[:, None, None]
        gc = fill * (1 - t) + g2 * t
        sub[..., :3] = gc * m[..., None] + sub[..., :3] * (1 - m[..., None])
    return layer

def composite(base, layer):
    a = layer[..., 3:4] / 255
    b = base.astype(float)
    out = b.copy()
    ba = b[..., 3:4] / 255
    oa = a + ba * (1 - a)
    out[..., :3] = (layer[..., :3] * a + b[..., :3] * ba * (1 - a)) / np.maximum(oa, 1e-6)
    out[..., 3:4] = oa * 255
    return out

def inpaint(img, box):
    import cv2
    x, y, w, h = box
    m = np.zeros(img.shape[:2], np.uint8); m[y:y + h, x:x + w] = 255
    rgb = np.ascontiguousarray(img[..., :3].astype(np.uint8))
    r = cv2.inpaint(rgb, m, 5, cv2.INPAINT_TELEA)
    img[y:y + h, x:x + w, :3] = r[y:y + h, x:x + w]
    return img

def depth_table(reg, t0):
    """Index used at each depth (distance from the transparent outside) in an original glyph region."""
    import cv2
    m = (reg != t0).astype(np.uint8)
    dist = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
    tab = {}
    for b in np.unique(np.round(dist[m > 0] * 2) / 2):
        sel = (np.round(dist * 2) / 2 == b) & (m > 0)
        v, c = np.unique(reg[sel], return_counts=True)
        tab[float(b)] = int(v[np.argmax(c)])
    return tab

def apply_index(idx, op, W, H):
    """Palette-agnostic text: silhouette depth -> index layering copied from the original element."""
    import cv2
    x, y, w, h = op['box']
    sx, sy, sw, sh = op.get('style_from', op['box'])
    t0 = op.get('t0', 0)
    tab = depth_table(idx[sy:sy + sh, sx:sx + sw].copy(), t0)
    ex, ey, ew, eh = op['erase'] if isinstance(op.get('erase'), list) else op['box']
    if op.get('erase', True) is not False: idx[ey:ey + eh, ex:ex + ew] = t0
    o2 = dict(op, fill='#ffffff', outline='#ffffff', glow=0, grad=None)
    lay = render(o2, W, H)[..., 3] / 255
    m = (lay[y:y + h, x:x + w] > op.get('thr', 0.45)).astype(np.uint8)
    dist = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
    keys = np.array(sorted(tab)); vals = np.array([tab[k] for k in keys])
    b = np.round(dist * 2) / 2
    pos = np.clip(np.searchsorted(keys, b, side='right') - 1, 0, len(keys) - 1)
    new = vals[pos]
    sub = idx[y:y + h, x:x + w]
    sub[m > 0] = new[m > 0]

def apply(d, o, ops, preview=None):
    t, stride, idx, pal, rgba = load(d, o)
    if all(op.get('imode') for op in ops):
        H, W = idx.shape
        for op in ops:
            if 'text' in op: apply_index(idx, op, W, H)
            else:
                x, y, w, h = op['erase']; idx[y:y + h, x:x + w] = op.get('t0', 0)
        store(d, t, stride, idx)
        if preview:
            Image.fromarray(rgba[idx].astype(np.uint8)[:, :t['w']], 'RGBA').save(preview)
        return
    if ops and isinstance(ops[0], dict) and 'clut' in ops[0]:
        # multi-CLUT texture: edit in the space of a palette recovered from the emulator
        c = json.load(open('trans/clut_%s.json' % ops[0]['clut_file'], encoding='utf-8'))['pals'][ops[0]['clut']]
        rgba = np.array(c, int)
        if len(rgba) < len(pal): rgba = np.vstack([rgba, np.zeros((len(pal) - len(rgba), 4), int)])
    img = rgba[idx].astype(float)   # H x stride x 4
    H, W = img.shape[:2]
    orig_idx = idx.copy()
    for op in ops:
        if 'text' not in op:
            x, y, w, h = op['erase'] if 'erase' in op else op['box']
            if op.get('dfill'):
                cx, cy, r = op['diamond']; yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
                sel = (np.abs(xx - cx) + np.abs(yy - cy) < r)
                img[sel] = list(hexc(op['dfill'])) + [op.get('dalpha', 238)]
            elif op.get('color'):
                import cv2
                c = np.array(hexc(op['color']), float)
                reg = img[y:y + h, x:x + w]
                dd = np.sqrt(((reg[..., :3] - c) ** 2).sum(-1))
                m = np.zeros(img.shape[:2], np.uint8)
                m[y:y + h, x:x + w] = ((dd < op.get('tol', 60)) & (reg[..., 3] > 40)).astype(np.uint8) * 255
                m = cv2.dilate(m, np.ones((2 * op.get('grow', 1) + 1,) * 2, np.uint8))
                if op.get('diamond'):
                    cx, cy, r = op['diamond']; yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
                    m[np.abs(xx - cx) + np.abs(yy - cy) >= r] = 0
                rgb = np.ascontiguousarray(np.clip(img[..., :3], 0, 255).astype(np.uint8))
                img[..., :3] = cv2.inpaint(rgb, m, 4, cv2.INPAINT_TELEA)
                al = np.ascontiguousarray(np.clip(img[..., 3], 0, 255).astype(np.uint8))
                img[..., 3] = cv2.inpaint(al, m, 4, cv2.INPAINT_TELEA)
            elif op.get('interp'):
                L = img[y:y + h, x - 1:x].copy(); R = img[y:y + h, x + w:x + w + 1].copy()
                tt = np.linspace(0, 1, w + 2)[1:-1][None, :, None]
                img[y:y + h, x:x + w] = L * (1 - tt) + R * tt
            elif op.get('inpaint') or op.get('fillc'):
                if op.get('fillc'): img[y:y + h, x:x + w, :3] = hexc(op['fillc'])
                else: img = inpaint(img, (x, y, w, h))
            else: img[y:y + h, x:x + w] = 0
            continue
        if 'style_from' in op:
            f, ou = sample_style(img, op['style_from'])
            op = dict(op); op.setdefault('fill', f); op.setdefault('outline', ou)
        op = dict(op); op.setdefault('fill', '#ffffff'); op.setdefault('outline', '#000000')
        if op.get('erase', True) is not False:
            x, y, w, h = op['erase'] if isinstance(op.get('erase'), list) else op['box']
            if op.get('inpaint'): img = inpaint(img, (x, y, w, h))
            else: img[y:y + h, x:x + w] = 0
        if op.get('cut'):
            lay = render(op, W, H)[..., 3] / 255
            img[..., 3] *= (1 - lay)
        else:
            img = composite(img, render(op, W, H))
    base = rgba[orig_idx].astype(float)
    ch = (np.abs(img - base) > 0.5).any(-1)
    new = orig_idx.copy()
    if ops and 'clut' in ops[0]:
        # per element: only indices that element already used (one per colour, most frequent),
        # so the texture's other CLUTs still see the same index layering
        for op in ops:
            b = op.get('box') or op.get('erase')
            if not isinstance(b, list): continue
            x, y, w, h = b
            sel = np.zeros(idx.shape, bool); sel[y:y + h, x:x + w] = True; sel &= ch
            if not sel.any(): continue
            reg = orig_idx[y:y + h, x:x + w].reshape(-1)
            v, c = np.unique(reg, return_counts=True)
            best = {}
            for vi, ci in sorted(zip(v, c), key=lambda t: -t[1]):
                best.setdefault(tuple(rgba[vi]), int(vi))
            allowed = np.array(sorted(best.values()))
            q = quantize(np.clip(img[sel], 0, 255)[:, None, :], rgba[allowed])[:, 0]
            new[sel] = allowed[q]; ch &= ~sel
    if ch.any(): new[ch] = quantize(np.clip(img[ch], 0, 255)[:, None, :], rgba)[:, 0]
    if ops and 'clut' in ops[0]:
        # only touch the edited rectangles; everything else keeps its exact indices
        keep = np.ones(idx.shape, bool)
        for op in ops:
            for b in (op.get('box'), op.get('erase') if isinstance(op.get('erase'), list) else None):
                if b: keep[b[1]:b[1] + b[3], b[0]:b[0] + b[2]] = False
        new[keep] = orig_idx[keep]
    for op in ops:
        # glow labels stored as a depth ramp (0 = clear .. 15 = glyph core); every CLUT colours the ramp
        if 'text' in op and op.get('depth'):
            import cv2
            x, y, w, h = op['box']
            m = render(dict(op, outline='#ffffff', ow=0, glow=0), W, H)[..., 3] > 110
            dist = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 3)
            dep = np.where(m, op.get('core', 15), np.clip(np.round(7 - dist * 1.1), 0, 6)).astype(new.dtype)
            sl = (slice(y, y + h), slice(x, x + w))
            new[sl] = dep[sl]
    store(d, t, stride, new)
    if preview:
        Image.fromarray(rgba[new].astype(np.uint8)[:, :t['w']], 'RGBA').save(preview)

def patch_all(read_entry, previews=None):
    """read_entry(fileno) -> bytearray (cached by caller). Returns set of modified file numbers."""
    spec = json.load(open('trans/images.json', encoding='utf-8'))
    idx = {('%s_%02d' % (x['f'], x['k'])): x for x in json.load(open('work/tex/index.json'))}
    touched = set()
    for key, ops in spec.items():
        if key.startswith('_'): continue
        x = idx[key]; f = int(x['f'])
        d = read_entry(f)
        apply(d, x['o'], ops, previews and '%s/%s.png' % (previews, key))
        touched.add(f)
    return touched
