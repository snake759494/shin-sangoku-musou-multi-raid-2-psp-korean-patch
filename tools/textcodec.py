"""Game text <-> JSON text. Control: \n = 0x0A, {Cx} = ESC 'C' x (colour), {R} = ESC 'R', {Px} = ESC 'P' x (icon)."""
import re, sys
sys.path.insert(0, 'tools')
from charmap import table
TSET = set(table())
JP = re.compile('[ぁ-んァ-ヶ一-龠々〆①-⑳Ⅰ-Ⅹ㍉㌶㌃㍑㌍㌦㌣㌫㍊㌻㎜㎝㎞㎎㍍㌘㌧]')

def decode(b, o=0, maxlen=4000):
    s = []; i = o; n = min(len(b), o + maxlen)
    while i < n:
        c = b[i]
        if c == 0: return ''.join(s), i - o
        if c == 0x0a: s.append('\n'); i += 1; continue
        if c == 0x1b and i + 1 < n:
            k = chr(b[i + 1])
            if k == 'R': s.append('{R}'); i += 2; continue
            if k in 'CP' and i + 2 < n and chr(b[i + 2]) in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                s.append('{%s%s}' % (k, chr(b[i + 2]))); i += 3; continue
            return None, i - o
        if 0x20 <= c < 0x7f: s.append(chr(c)); i += 1; continue
        if i + 1 < n and ((c << 8) | b[i + 1]) in TSET:
            s.append(bytes(b[i:i + 2]).decode('cp932', 'replace')); i += 2; continue
        return None, i - o
    return None, i - o

TOK = re.compile(r'\{(R|[CP][0-9A-Z])\}')
def encode(s, enc_chars):
    out = bytearray(); pos = 0
    for m in TOK.finditer(s):
        out += enc_chars(s[pos:m.start()].replace('\n', '\x0a')) if pos < m.start() else b''
        out += b'\x1b' + m.group(1).encode()
        pos = m.end()
    out += enc_chars(s[pos:])
    return bytes(out)
