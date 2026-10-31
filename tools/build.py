"""Build the Korean ISO.
  python tools/build.py OUT.iso
trans/eboot_ko.json  {jp: ko}   EBOOT string pool (relocated through data pointers when longer)
trans/stage_ko.json  {jp: ko}   64-byte message slots in LINKDATA (in place, <=63 bytes)
"""
import json, os, re, struct, sys, shutil
sys.path.insert(0, 'tools')
from charmap import build as build_map, encoder
from textcodec import encode as tencode
from fontpatch import patch as font_patch
import linkdata
from isobuild import Iso

SRC = 'Shin Sangoku Musou - Multi Raid 2 (Japan).iso'
VBASE = 0x8804000 - 0x54

def load(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}

def all_ko():
    s = ''
    for p in ('trans/eboot_ko.json', 'trans/stage_ko.json'):
        s += ''.join(load(p).values())
    return s

def patch_eboot(elf, enc, tr, strings, log):
    """Every translated string with data references is repacked: the slots of all
    such strings are merged into contiguous regions and refilled, pointers updated."""
    e = bytearray(elf)
    items = []
    for x in strings:
        ko = tr.get(x['jp'])
        if ko is None: continue
        b = tencode(ko, enc)
        if not x['refs']:
            if len(b) <= x['cap']:
                e[x['o']:x['o'] + x['cap'] + 1] = b + bytes(1) * (x['cap'] + 1 - len(b))
            else:
                log.append('EBOOT overflow (no ref) %x %s' % (x['o'], ko))
            continue
        items.append((x, b))
    slots = sorted((x['o'], x['o'] + x['cap'] + 1) for x, b in items)
    regions = []
    for a, z in slots:
        if regions and regions[-1][1] == a: regions[-1][1] = z
        else: regions.append([a, z])
    for a, z in regions: e[a:z] = bytes(1) * (z - a)
    # dedupe identical encoded strings, place longest first (first fit)
    placed = {}
    order = sorted(items, key=lambda t: -len(t[1]))
    for x, b in order:
        if b in placed:
            addr = placed[b]
        else:
            need = len(b) + 1
            for r in regions:
                if r[1] - r[0] >= need:
                    addr = r[0]; e[addr:addr + len(b)] = b; r[0] += need
                    break
            else:
                log.append('EBOOT no space %x %s' % (x['o'], tr[x['jp']])); continue
            placed[b] = addr
        for r in x['refs']:
            if not 0x3ff5e0 <= r < 0x47a904: continue   # .data only (module info gp happens to match a string)
            struct.pack_into('<I', e, r, addr + VBASE)
    log.append('EBOOT strings %d, free left %d (largest %d)' % (len(items), sum(z - a for a, z in regions), max([z - a for a, z in regions] or [0])))
    return bytes(e)

def patch_namegrid(elf, enc, text):
    """Name-entry grid: kana/kanji cells -> most frequent Korean syllables (sorted)."""
    e = bytearray(elf)
    for i, t in enumerate(['한글1', '한글2', '한글3', '영숫자', '특수']):
        b = tencode(t, enc); e[0x477018 + i * 8:0x477020 + i * 8] = b + bytes(8 - len(b))
    cells = []
    for o in range(0x477040, 0x477a00, 4):
        t = bytes(e[o:o + 4]).rstrip(b'\0')
        try: c = t.decode('cp932')
        except UnicodeDecodeError: continue
        if c == '' or re.match('[ぁ-ゟァ-ヺ一-鿿]$', c): cells.append(o)
    freq = {}
    names = ''.join(json.load(open('trans/names.json', encoding='utf-8')).values())
    for ch in text + names * 20:
        if '가' <= ch <= '힣': freq[ch] = freq.get(ch, 0) + 1
    syl = sorted(sorted(freq, key=lambda c: -freq[c])[:len(cells)])
    for o, ch in zip(cells, syl):
        b = tencode(ch, enc); e[o:o + 4] = b + bytes(4 - len(b))
    return bytes(e)

def main(out):
    log = []
    T, m = build_map(all_ko())
    enc = encoder(m, T)
    json.dump({k: v[1] for k, v in m.items()}, open('work/charmap.json', 'w', encoding='utf-8'), ensure_ascii=False)
    fonts = font_patch(m)
    elf = open('work/eboot/EBOOT.ELF', 'rb').read()
    elf = patch_eboot(elf, enc, load('trans/eboot_ko.json'), json.load(open('work/eboot_strings.json', encoding='utf-8')), log)
    if not os.environ.get("NOGRID"): elf = patch_namegrid(elf, enc, all_ko())
    # LINKDATA entries
    entries = {int(k): bytearray(v) for k, v in fonts.items()}
    st = load('trans/stage_ko.json')
    for x in json.load(open('work/stage_slots.json', encoding='utf-8')):
        ko = st.get(x['jp'])
        if ko is None: continue
        b = tencode(ko, enc)
        if len(b) > 63:
            log.append('STAGE overflow %s %s (%d)' % (x['f'], ko, len(b))); continue
        i = int(x['f'])
        if i not in entries: entries[i] = bytearray(open('work/link/%05d.bin' % i, 'rb').read())
        entries[i][x['o']:x['o'] + 64] = b + b'\0' * (64 - len(b))
    # image textures (in place, same size and palette)
    import imgpatch
    def entry(i):
        if i not in entries: entries[i] = bytearray(open('work/link/%05d.bin' % i, 'rb').read())
        return entries[i]
    log.append('images: %d files' % len(imgpatch.patch_all(entry)))
    iso = Iso(SRC, out)
    _, _, _, llba, lsize = iso.find('/PSP_GAME/USRDIR/LINKDATA.BIN')
    n, offs, sizes = linkdata.header()
    for i, data in entries.items():
        assert len(data) == sizes[i]
        iso.f.seek(llba * 2048 + offs[i] * 2048); iso.f.write(data)
    print(iso.replace('/PSP_GAME/SYSDIR/EBOOT.BIN', elf))
    # movies with burned-in Korean subtitles (same size, audio/timestamps untouched)
    for p in sorted(os.listdir('work/mvbuild/patched')) if os.path.isdir('work/mvbuild/patched') else []:
        if p.endswith('.pmf'):
            log.append('movie %s %s' % (p, iso.replace('/PSP_GAME/USRDIR/Data/Movie/' + p, open('work/mvbuild/patched/' + p, 'rb').read())))
    iso.close()
    open('work/build.log', 'w', encoding='utf-8').write('\n'.join(log))
    print('\n'.join(log[-15:]))

if __name__ == '__main__':
    main(sys.argv[1])
