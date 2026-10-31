"""Replace video only, keeping every original PTS anchor in its sector.

Unlike a generic remux, audio PES bytes, SCRs, the PSMF header, metadata,
sector count and file size remain exact. Each original timestamp packet
starts with the same numbered access unit. Spare space is MPEG padding,
never long zero runs inside the AVC stream.
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
        body = (b'\0'*4 if fa else b'') + new[starts[fa]:starts[fb]]
        group = slots[a:b]
        # Reserve a legal six-byte padding packet in every used PES slot.
        capacities = [max(0, cap - 6) for _, _, cap in group]
        capacity = sum(capacities)
        if len(body) > capacity:
            raise ValueError(f'anchor {fa}:{fb}: {len(body)} > {capacity}')
        consumed = weight = 0
        for (si, qi, cap), usable in zip(group, capacities):
            q = d.sectors[si].packets[qi]
            weight += usable
            end = len(body) * weight // capacity
            piece = body[consumed:end]
            consumed = end
            if not piece:
                assert not q.flags2 & 0x80
                raw = b'\0\0\1\xbe' + struct.pack('>H', len(q.raw)-6) + b'\xff'*(len(q.raw)-6)
            else:
                hdr = bytearray(q.raw[:q.payload_off])
                struct.pack_into('>H', hdr, 4, len(hdr)-6+len(piece))
                gap = len(q.raw)-len(hdr)-len(piece)
                assert gap >= 6
                raw = bytes(hdr)+piece+b'\0\0\1\xbe'+struct.pack('>H',gap-6)+b'\xff'*(gap-6)
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
