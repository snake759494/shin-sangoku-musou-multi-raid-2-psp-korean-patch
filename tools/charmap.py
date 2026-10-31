"""Korean syllable -> game code. The game's glyph table (EBOOT 0x08C5879C, 3255 sorted SJIS codes)
is kept; symbol codes < 0x829F stay, every other slot gets a Hangul syllable (sorted by Unicode)."""
import struct, json, os
ELF = 'work/eboot/EBOOT.ELF'
TAB_OFF = 0x8C5879C - 0x8804000 + 0x54
NTAB = 3255
KEEP_BELOW = 0x829F

def table():
    e = open(ELF, 'rb').read()
    return list(struct.unpack_from('<%dI' % NTAB, e, TAB_OFF))

def ks_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try: out.append(bytes([hi, lo]).decode('euc-kr'))
            except UnicodeDecodeError: pass
    return out

def build(extra=''):
    T = table()
    free = [i for i, c in enumerate(T) if c >= KEEP_BELOW]
    chars = sorted(set(ks_hangul()) | {c for c in extra if '\uac00' <= c <= '\ud7a3'})
    assert len(chars) <= len(free), (len(chars), len(free))
    m = {}
    for ch, i in zip(chars, free):
        m[ch] = (i, T[i])
    return T, m

def encoder(m, T):
    keep = {bytes([c >> 8, c & 255]).decode('cp932'): c for c in T if c < KEEP_BELOW}
    def enc(s):
        out = bytearray()
        for ch in s:
            if ch in m:
                c = m[ch][1]; out += bytes([c >> 8, c & 255])
            elif ch in keep:
                c = keep[ch]; out += bytes([c >> 8, c & 255])
            elif ord(ch) < 0x7f:
                out.append(ord(ch))
            else:
                raise ValueError('unmappable %r in %r' % (ch, s))
        return bytes(out)
    return enc
