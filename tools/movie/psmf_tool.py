"""psmf_tool.py -- SONY PSMF (.PMF) demux / remux for VC2 (PSP) movies.

PMF layout:
    [0x800-byte PSMF header][MPEG-PS stream, 0x800-aligned sectors]

Each 2048-byte sector = one MPEG-2 pack header (000001BA, 14 bytes here)
followed by one or more PES packets, zero-padded to the 2048 boundary.
Sector 0 (and each segment-start sector) additionally carries a 000001BB
system header and a 000001BF PSMF-private (metadata/EP) packet before the
first 000001E0 video PES.

PES stream ids:
    0xBA pack header, 0xBB system header, 0xBF PSMF-private (metadata),
    0xBE padding, 0xE0 video (H.264), 0xBD private_stream_1 (ATRAC3+ audio).

This module provides:
    demux(pmf_bytes)  -> DemuxResult   (structural, lossless)
    remux(dmx, new_h264=None) -> bytes  (byte-exact when new_h264 is None)

The identity path is a faithful structural reconstruction (not a raw copy):
every sector is rebuilt from its parsed components, so a byte-exact result
proves the parse captured 100% of the container.  The re-encode path
replaces the video elementary stream while preserving the original audio
PES verbatim, the original sector *grid* (pack SCRs, segment BB/BF packets),
and rebuilds only the video PES timestamps/payloads.
"""

import struct

SECTOR = 0x800
HDR_SIZE = 0x800
PACK_LEN = 14  # 000001BA + 10 bytes (no stuffing observed in VC2 files)


# --------------------------------------------------------------------------
# low-level PES parsing
# --------------------------------------------------------------------------

def _u16(b, o):
    return (b[o] << 8) | b[o + 1]


def _find_start(sec, o):
    """Return index of next 00 00 01 start code at/after o, or -1."""
    n = len(sec)
    while o + 3 <= n:
        if sec[o] == 0 and sec[o + 1] == 0 and sec[o + 2] == 1:
            return o
        o += 1
    return -1


class PES:
    """One PES packet parsed within a sector."""
    __slots__ = ("sid", "raw", "hdr_len_field", "flags1", "flags2",
                 "pes_hdrlen", "payload_off", "payload")

    def __init__(self, sid, raw):
        self.sid = sid
        self.raw = raw            # full bytes: 000001 sid llhh ...payload
        self.flags1 = None
        self.flags2 = None
        self.pes_hdrlen = None
        self.payload_off = None   # offset of payload within raw
        self.payload = None
        # length field (bytes after the 6-byte 000001 sid ll hh prefix)
        self.hdr_len_field = _u16(raw, 4)
        if sid in (0xE0, 0xBD):
            self.flags1 = raw[6]
            self.flags2 = raw[7]
            self.pes_hdrlen = raw[8]
            self.payload_off = 9 + self.pes_hdrlen
            end = 6 + self.hdr_len_field
            self.payload = raw[self.payload_off:end]


class Sector:
    """One 2048-byte sector: pack header + list of PES packets + pad."""
    __slots__ = ("index", "pack", "packets", "pad")

    def __init__(self, index):
        self.index = index
        self.pack = None       # 14-byte pack header raw
        self.packets = []      # list[PES]
        self.pad = b""         # trailing pad bytes (usually zeros)

    @property
    def kind(self):
        # classification by the last "content" PES (E0/BD) in the sector,
        # falling back to whatever is present.
        for p in self.packets:
            if p.sid in (0xE0, 0xBD):
                return p.sid
        return self.packets[-1].sid if self.packets else None


def _parse_sector(sec, index):
    """Parse one 2048-byte sector into a Sector object."""
    s = Sector(index)
    assert sec[:4] == b"\x00\x00\x01\xba", "sector %d missing pack header" % index
    stuff = sec[13] & 0x7
    plen = PACK_LEN + stuff
    s.pack = sec[:plen]
    o = plen
    while True:
        if o + 4 > SECTOR:
            break
        if sec[o] != 0 or sec[o + 1] != 0 or sec[o + 2] != 1:
            # not a start code -> rest is padding
            break
        sid = sec[o + 3]
        if sid == 0xBA:  # another pack header inside a sector (unexpected)
            break
        length = _u16(sec, o + 4)
        raw = sec[o:o + 6 + length]
        s.packets.append(PES(sid, raw))
        o += 6 + length
    s.pad = sec[o:]
    return s


# --------------------------------------------------------------------------
# demux
# --------------------------------------------------------------------------

class DemuxResult:
    def __init__(self):
        self.header = b""          # 0x800 PSMF header
        self.sectors = []          # list[Sector] in file order
        self.orig_size = 0
        # convenience views (built lazily)
        self._h264 = None

    @property
    def num_sectors(self):
        return len(self.sectors)

    def video_es(self):
        """Concatenate all 0xE0 PES payloads in sector order -> Annex-B .264."""
        if self._h264 is None:
            buf = bytearray()
            for sec in self.sectors:
                for p in sec.packets:
                    if p.sid == 0xE0:
                        buf += p.payload
            self._h264 = bytes(buf)
        return self._h264

    def audio_pes(self):
        """List of (sector_index, raw_pes_bytes) for every 0xBD packet."""
        out = []
        for sec in self.sectors:
            for p in sec.packets:
                if p.sid == 0xBD:
                    out.append((sec.index, p.raw))
        return out


def demux(pmf_bytes):
    if pmf_bytes[:4] != b"PSMF":
        raise ValueError("not a PSMF file")
    dmx = DemuxResult()
    dmx.orig_size = len(pmf_bytes)
    dmx.header = pmf_bytes[:HDR_SIZE]
    o = HDR_SIZE
    idx = 0
    while o + SECTOR <= len(pmf_bytes):
        dmx.sectors.append(_parse_sector(pmf_bytes[o:o + SECTOR], idx))
        o += SECTOR
        idx += 1
    if o != len(pmf_bytes):
        raise ValueError("stream not a whole multiple of sector size")
    return dmx


# --------------------------------------------------------------------------
# sector reconstruction (identity)
# --------------------------------------------------------------------------

def _rebuild_sector(sec):
    """Reconstruct the exact 2048-byte sector from its parsed parts."""
    out = bytearray()
    out += sec.pack
    for p in sec.packets:
        out += p.raw
    out += sec.pad
    if len(out) != SECTOR:
        raise ValueError("rebuilt sector %d length %d != %d"
                         % (sec.index, len(out), SECTOR))
    return bytes(out)


# --------------------------------------------------------------------------
# PTS/DTS codec (5-byte marker format)
# --------------------------------------------------------------------------

def _read_ts(b, o):
    v = ((b[o] >> 1) & 0x7) << 30
    v |= b[o + 1] << 22
    v |= (b[o + 2] >> 1) << 15
    v |= b[o + 3] << 7
    v |= b[o + 4] >> 1
    return v


def _write_ts(v, guard):
    # guard nibble: 0x2 for PTS-only, 0x3 for PTS(with DTS), 0x1 for DTS
    b0 = (guard << 4) | (((v >> 30) & 0x7) << 1) | 1
    b1 = (v >> 22) & 0xFF
    b2 = (((v >> 15) & 0x7F) << 1) | 1
    b3 = (v >> 7) & 0xFF
    b4 = ((v & 0x7F) << 1) | 1
    return bytes([b0, b1, b2, b3, b4])


# --------------------------------------------------------------------------
# remux
# --------------------------------------------------------------------------

def _patch_header(header, new_stream_size):
    h = bytearray(header)
    struct.pack_into(">I", h, 0x0C, new_stream_size)
    return bytes(h)


def remux(dmx, new_h264=None):
    """Rebuild a PMF.

    new_h264 is None -> byte-exact identity reconstruction.
    new_h264 given  -> replace the video elementary stream, keep audio +
                       sector grid; regenerate video PES.
    """
    if new_h264 is None:
        return _remux_identity(dmx)
    return _remux_reencode(dmx, new_h264)


def _remux_identity(dmx):
    out = bytearray(dmx.header)
    for sec in dmx.sectors:
        out += _rebuild_sector(sec)
    if len(out) != dmx.orig_size:
        # size still fine, but patch stream_size to match anyway
        pass
    # header stream_size should already match; recompute to be safe
    stream_size = len(out) - HDR_SIZE
    out[0x0C:0x10] = struct.pack(">I", stream_size)
    return bytes(out)


# ---- re-encode remux ------------------------------------------------------
#
# Strategy: walk the ORIGINAL sector grid.  Emit every non-video sector
# (audio 0xBD, and segment sectors carrying BB/BF) verbatim.  For runs of
# video sectors, we splice the NEW H.264 access units into the same set of
# sector slots, reusing the original per-slot pack header (SCR) and the
# original video PES timestamp template so the mux schedule stays valid.
#
# Video sectors come in AUs: the first E0 of an AU carries a PES header with
# PTS/DTS and starts with 00000001 09 (AUD).  Continuation E0 sectors have
# flags2=0 / hdrlen=0 and raw payload.  We collect the ORIGINAL video-sector
# slots (their pack headers + first-of-AU PES templates), split the new .264
# into AUs, and re-lay them into those slots.


def _split_au(h264):
    """Split an Annex-B stream into access units at AUD (00 00 00 01 09)."""
    aus = []
    n = len(h264)
    # find all AUD positions
    positions = []
    i = 0
    while i + 5 <= n:
        if h264[i] == 0 and h264[i + 1] == 0 and h264[i + 2] == 0 \
                and h264[i + 3] == 1 and h264[i + 4] == 9:
            positions.append(i)
            i += 5
        else:
            i += 1
    if not positions:
        return [h264]
    for k, p in enumerate(positions):
        end = positions[k + 1] if k + 1 < len(positions) else n
        aus.append(h264[p:end])
    return aus


def _collect_video_slots(dmx):
    """Return list of video sector slots.

    Each slot records its pack header, the video 0xE0 PES, and any
    segment-start prefix packets (0xBB system header + 0xBF PSMF-private)
    that must be preserved VERBATIM before the video PES.
    """
    slots = []
    for sec in dmx.sectors:
        vids = [p for p in sec.packets if p.sid == 0xE0]
        if not vids:
            continue
        p = vids[0]
        first = (p.flags2 not in (0, None))  # first-of-AU carries PTS
        tmpl = p.raw[:p.payload_off] if p.payload_off else p.raw[:6]
        # verbatim prefix = all packets before the E0 (BB/BF at segment starts)
        prefix = b""
        for q in sec.packets:
            if q.sid == 0xE0:
                break
            prefix += q.raw
        slots.append({
            "index": sec.index,
            "sector": sec,
            "pack": sec.pack,
            "pes": p,
            "first": first,
            "tmpl": tmpl,
            "prefix": prefix,   # BB+BF bytes to keep before the video PES
        })
    return slots


def _make_video_pes_header(payload_len, pts=None, dts=None):
    """Build a 000001E0 PES header for a given payload length.

    If pts (and optionally dts) is given -> flags2 with PTS[+DTS], hdrlen
    sized to the timestamp bytes.  Otherwise a bare continuation header
    (flags2=0, hdrlen=0).
    """
    if pts is None:
        # continuation PES: flags1=0x81 (MPEG-2 '10' marker), flags2=0, hdrlen=0
        pes = bytearray(b"\x00\x00\x01\xe0\x00\x00\x81\x00\x00")
        struct.pack_into(">H", pes, 4, 3 + payload_len)  # flags1,flags2,hdrlen
        return bytes(pes)
    if dts is not None:
        ts = _write_ts(pts, 0x3) + _write_ts(dts, 0x1)
        flags2 = 0xC0
    else:
        ts = _write_ts(pts, 0x2)
        flags2 = 0x80
    hdrlen = len(ts)
    pes = bytearray(b"\x00\x00\x01\xe0\x00\x00")
    pes.append(0x81)         # flags1
    pes.append(flags2)       # flags2
    pes.append(hdrlen)       # PES_header_data_length
    pes += ts
    body_len = 3 + hdrlen + payload_len  # flags1+flags2+hdrlen + hdr + payload
    struct.pack_into(">H", pes, 4, body_len)
    return bytes(pes)


def _make_video_sector(pack, payload, pts=None, dts=None, prefix=b""):
    """Build a full 2048-byte video sector.

    prefix = verbatim bytes (segment-start BB system header + BF metadata)
    emitted between the pack header and the video PES.
    """
    hdr = _make_video_pes_header(len(payload), pts, dts)
    out = bytearray()
    out += pack
    out += prefix
    out += hdr
    out += payload
    if len(out) > SECTOR:
        raise ValueError("video sector overflow: %d > %d" % (len(out), SECTOR))
    out += b"\x00" * (SECTOR - len(out))
    return bytes(out)


# frame cadence (90kHz).  firstPTS = 90000 (1.0s start), delta = 90000/29.97.
FRAME_DELTA = 3003
FIRST_PTS = 90000


def _aud_offsets(es):
    """Byte offsets of every access-unit delimiter (NAL type 9) in Annex-B es."""
    out = []
    i, n = 0, len(es)
    while i + 4 < n:
        if es[i] == 0 and es[i + 1] == 0 and es[i + 2] == 1 and (es[i + 3] & 0x1f) == 9:
            out.append(i)
            i += 4
        else:
            i += 1
    return out


# The original marks ~1 video PES in 14 frames with a PTS anchor
# (PTS = 90000 + frame*3003); per-frame pic_timing SEI (from the encoder's HRD)
# supplies the timing between anchors.  We reproduce that cadence.
ANCHOR_FRAME_GAP = 14


def video_capacity(dmx):
    """Total video-payload bytes available across all video sectors (assuming a
    no-PTS 9-byte PES header each).  Target the re-encoded ES near this so the
    video fills the grid and stays interleave-aligned with the audio."""
    total = 0
    for sec in dmx.sectors:
        e0 = [p for p in sec.packets if p.sid == 0xE0]
        if not e0:
            continue
        prefix = 0
        for q in sec.packets:
            if q.sid == 0xE0:
                break
            prefix += len(q.raw)
        total += SECTOR - len(sec.pack) - prefix - 9
    return total


def _remux_reencode(dmx, new_h264):
    """Replace ONLY the video pixel bytes, keeping the original PMF structure
    byte-for-byte otherwise (pack SCRs, video PES headers + PTS, audio, sector
    grid, header — all verbatim).

    The PSP hardware Media Engine validates the mux buffer model: the pack-header
    SCR (arrival clock) and the video PTS must keep the original ~1s relationship,
    or the fixed video buffer overflows and hardware errors (PPSSPP's dynamic
    buffers hide it).  So we (1) byte-ALIGN each re-encoded frame to the SAME ES
    offset as the original's corresponding frame -- padding the gaps with leading
    ZERO bytes (valid Annex-B leading_zero_8bits before the next start code, NOT
    filler NALs) -- to exactly the original ES length, then (2) drop that aligned
    ES into the ORIGINAL video-PES payload slots, reusing every original PES header
    (hence every PTS) and pack header unchanged.  Result: identical container +
    timing, only the coded pixels differ.

    The encoder must still emit an ME-legal AVC stream (Main@L<=3, CABAC, ref=1,
    no B-frames, weightp=0, AUD + buffering_period/pic_timing SEI + HRD).  The new
    stream must have the same frame count as the original and fit the original's
    total video payload budget (else ValueError -> caller lowers bitrate).
    """
    orig_es = dmx.video_es()
    O = _aud_offsets(orig_es)
    A = _aud_offsets(new_h264)
    if not O or len(A) != len(O):
        raise ValueError("frame-count mismatch (new %d vs orig %d); cannot align"
                         % (len(A), len(O)))

    # byte-align frame k to the original's offset O[k], but never overrun the
    # original ES length: frame k may start no later than (budget - bytes still
    # to come), so the tail packs tighter if a few frames ran big.  In the common
    # case O[k] is well within budget and alignment is exact.
    ends = A[1:] + [len(new_h264)]
    budget = len(orig_es)
    sizes = [ends[k] - A[k] for k in range(len(A))]
    suffix = 0                                    # total new-frame bytes from k..end
    suf = [0] * (len(A) + 1)
    for k in range(len(A) - 1, -1, -1):
        suffix += sizes[k]; suf[k] = suffix
    if suf[0] > budget:
        raise ValueError("re-encoded video (%d) exceeds original video capacity "
                         "(%d); lower bitrate" % (suf[0], budget))
    buf = bytearray(); p = 0
    for k in range(len(A)):
        target = min(O[k], budget - suf[k])       # cap so all remaining frames fit
        if p < target:
            buf += b"\x00" * (target - p); p = target
        buf += new_h264[A[k]:ends[k]]; p += sizes[k]
    aligned = bytes(buf) + b"\x00" * (budget - len(buf))   # exact orig length

    # swap the aligned ES into the original video-PES payload slots, in order
    out = bytearray(dmx.header)
    es_pos = 0
    for sec in dmx.sectors:
        if not any(q.sid == 0xE0 for q in sec.packets):
            out += _rebuild_sector(sec)
            continue
        newsec = bytearray(sec.pack)
        for q in sec.packets:
            if q.sid == 0xE0:
                plen = len(q.payload)
                newsec += q.raw[:q.payload_off] + aligned[es_pos:es_pos + plen]
                es_pos += plen
            else:
                newsec += q.raw
        newsec += sec.pad
        if len(newsec) != SECTOR:
            raise ValueError("rebuilt video sector %d len %d != %d"
                             % (sec.index, len(newsec), SECTOR))
        out += bytes(newsec)

    stream_size = len(out) - HDR_SIZE
    out[0x0C:0x10] = struct.pack(">I", stream_size)
    return bytes(out)


# --------------------------------------------------------------------------
# CLI / self-test
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    for fn in sys.argv[1:]:
        data = open(fn, "rb").read()
        dmx = demux(data)
        rt = remux(dmx)
        ok = rt == data
        print("%s identity=%s (%d sectors, %d video, %d audio)" % (
            fn, ok, dmx.num_sectors,
            sum(1 for s in dmx.sectors if s.kind == 0xE0),
            sum(1 for s in dmx.sectors if s.kind == 0xBD)))
        if not ok:
            for i in range(min(len(rt), len(data))):
                if rt[i] != data[i]:
                    print("  first diff at 0x%X" % i)
                    break
