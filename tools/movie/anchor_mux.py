"""Replace video only, keeping every original PTS anchor in its sector.

Unlike a generic remux, audio PES bytes, SCRs, the PSMF header, metadata,
sector count and file size remain exact. Each original timestamp packet
starts with the same numbered access unit. Spare space is an AVC filler-data NAL,
so every PES slot stays full as in the shipped file.
"""
import bisect
import struct
import psmf_tool as P


def layout(d):
    es = d.video_es()
    starts = P._aud_offsets(es)
    slots, anchors = [], []
    pos = 0
    for si, sec in enumerate(d.sectors):
        for qi, q in enumerate(sec.packets):
            if q.sid != 0xE0:
                continue
            if q.flags2 & 0x80:
                frame = bisect.bisect_left(starts, pos)
                assert frame < len(starts) and starts[frame] < pos + len(q.payload)
                pts = P._read_ts(q.raw, 9)
                # A few original end sequences contain a one-frame PTS discontinuity.
                # Preserve the shipped timestamp instead of normalizing its clock.
                assert pts >= 90000
                anchors.append((len(slots), frame))
            slots.append((si, qi, len(q.payload)))
            pos += len(q.payload)
    assert anchors[0] == (0, 0)
    anchors.append((len(slots), len(starts)))
    return es, starts, slots, anchors


def remux(d, new):
    old, old_starts, slots, anchors = layout(d)
    starts = P._aud_offsets(new)
    assert len(starts) == len(old_starts), (len(starts), len(old_starts))
    starts.append(len(new))
    replacements = {}
    report = []
    for (a, fa), (b, fb) in zip(anchors, anchors[1:]):
        group = slots[a:b]
        # Fill every PES slot completely, like the shipped stream: spare bytes
        # become AVC filler-data NALs, so sectors keep their original packet
        # layout (no added MPEG padding packets). Filler goes to each frame
        # that is smaller than its original, so per-frame sizes (and the
        # decoder buffer) stay close to the shipped stream.
        capacity = sum(cap for _, _, cap in group)
        aus = [new[starts[f]:starts[f + 1]] for f in range(fa, fb)]
        lead = b'\0'*4 if fa else b''
        extra = capacity - len(lead) - sum(map(len, aus))
        if extra < 0:
            raise ValueError(f'anchor {fa}:{fb}: {capacity - extra} > {capacity}')
        fill = [0] * len(aus)
        for i, f in enumerate(range(fa, fb)):
            want = max(0, old_starts[f + 1] - old_starts[f] - len(aus[i]) if f + 1 < len(old_starts) else 0)
            fill[i] = min(want, extra); extra -= fill[i]
        fill[-1] += extra
        body = bytearray(lead)
        for au, n in zip(aus, fill):
            body += au
            if n >= 6: body += b'\0\0\0\1\x0c' + b'\xff' * (n - 6) + b'\x80'
            else: body += b'\0' * n
        body = bytes(body)
        consumed = 0
        for si, qi, cap in group:
            q = d.sectors[si].packets[qi]
            piece = body[consumed:consumed + cap]
            consumed += cap
            hdr = q.raw[:q.payload_off]
            raw = hdr + piece
            assert len(raw) == len(q.raw)
            replacements[si, qi] = raw
        assert consumed == len(body)
        report.append({'first_frame':fa,'end_frame':fb,'bytes':len(body),'capacity':capacity})
    out = bytearray(d.header)
    for si, sec in enumerate(d.sectors):
        raw = sec.pack+b''.join(replacements.get((si,qi),q.raw) for qi,q in enumerate(sec.packets))+sec.pad
        assert len(raw) == 2048
        out.extend(raw)
    check = P.demux(bytes(out))
    assert check.header == d.header
    assert len(P._aud_offsets(check.video_es())) == len(old_starts)
    assert len(check.sectors) == len(d.sectors)
    for oldsec, newsec in zip(d.sectors, check.sectors):
        assert oldsec.pack == newsec.pack
        for sid in (0xBD,0xBB,0xBF):
            assert [q.raw for q in oldsec.packets if q.sid==sid] == [q.raw for q in newsec.packets if q.sid==sid]
    _, _, _, newanchors = layout(check)
    assert [f for _,f in anchors] == [f for _,f in newanchors]
    return bytes(out), report
