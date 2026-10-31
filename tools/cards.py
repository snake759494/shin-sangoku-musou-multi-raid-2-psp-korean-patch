"""Character cards (LINKDATA 17564-17616): work/tex/cards_*.json -> trans/cards_ko.json -> trans/images.json ops."""
import json, glob, os, sys
sys.path.insert(0, 'tools')
from PIL import ImageFont

FONT = 'NanumSquareNeo-cBd.ttf'
SIZE = 14

def wrap(text, width, font):
    lines, line = [], ''
    for word in text.split(' '):
        cand = (line + ' ' + word).strip()
        if font.getlength(cand) <= width: line = cand; continue
        if line: lines.append(line)
        while font.getlength(word) > width:          # break over-long words by character
            k = len(word)
            while font.getlength(word[:k]) > width: k -= 1
            lines.append(word[:k]); word = word[k:]
        line = word
    if line: lines.append(line)
    return lines

def colour(n):
    if n <= 17576: return '#8aa8ff', '#1e2e80'      # Wei
    if n <= 17590: return '#ff5a6a', '#601020'      # Wu
    if n <= 17602: return '#6ad070', '#16481a'      # Shu
    return '#f0d060', '#6a4808'                     # others / immortals

def main():
    tr = {}
    if os.path.exists('trans/cards_ko.json'): tr = json.load(open('trans/cards_ko.json', encoding='utf-8'))
    for p in sorted(glob.glob('work/tex/cards_*.json')):
        tr.update(json.load(open(p, encoding='utf-8')))
    json.dump(tr, open('trans/cards_ko.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    S = json.load(open('trans/images.json', encoding='utf-8'))
    for key, c in tr.items():
        n = int(key[:5])
        from cardbox import body_box
        nx, ny, nw, nh = 262, 4, 100, 54
        ex, ey, ew, eh = body_box(key)
        bx, by, bw, bh = ex, ey, 206, 268 - ey
        size = SIZE
        while True:
            font = ImageFont.truetype(FONT, size)
            lines = wrap(c['ko'], bw - 4, font)
            lh = size + 4
            if len(lines) * lh <= max(eh + 20, 150) or size <= 10: break
            size -= 1
        f, g = colour(n)
        ops = [
            dict(erase=[nx - 2, ny - 2, nw + 4, nh + 4], inpaint=True),
            dict(erase=[ex - 3, ey - 3, ew + 6, eh + 6], inpaint=True),
            dict(text=c['name'], box=[nx, 18, 200, 40], font='brush', size=28,
                 fill=f, grad=g, outline='#101010', ow=1, align='l', erase=False, bold=1),
            dict(text='\n'.join(lines), box=[bx, by - 2, bw, len(lines) * lh + 4], font='gothicb', size=size, line_h=lh,
                 fill='#ffffff', outline='#141414', ow=1, align='l', valign='t', erase=False),
        ]
        ops[3]['box'][3] = min(ops[3]['box'][3], 272 - ops[3]['box'][1])
        S[key] = ops
    json.dump(S, open('trans/images.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(tr))

if __name__ == '__main__':
    main()
