"""
Magic Legion — wire codec (Phase 1 completion).

A schema-driven port of the client's `PacketStream`. It can encode/decode the BODY of any
of the 1630 `cb_net` messages from `../protocol/messages.json`, recursively handling
primitives, count-prefixed arrays, named structs, and Pair/Ternary tuples. It also frames
packets as [len][msgid][body].

A few wire details aren't fully determined by the static dump (they're marked below). They
are centralised here as flip-able constants and CONFIRMED from the client's first real
packet (the sniffer in gate.py auto-detects the framing). Field ORDER and TYPES come from
the schema and are exact.
"""
import struct, json, os

# ─────────────────────────── wire-format assumptions ───────────────────────────
# PacketStream wraps .NET BinaryReader/Writer  ⇒  little-endian scalars.
ENDIAN = "<"           # "<" LE (default) / ">" BE
COUNT_SIZE = "H"       # array/list count prefix: "H"=u16 (default) / "I"=u32
STR_LEN = "H"          # string byte-length prefix: "H"=u16 (default) / "I"=u32
# Frame header: [len][msgid][body].
FRAME_LEN = "H"        # length field width: "H"=u16 / "I"=u32
FRAME_MSGID = "I"      # msgid field width: "I"=u32 / "H"=u16  (all ids < 65536, so u16 fits)
FRAME_LEN_INCLUSIVE = True   # does `len` include the whole frame (len+msgid+body)?
# ────────────────────────────────────────────────────────────────────────────────

PRIM = {
    "bool": ("?", 1), "byte": ("B", 1), "sbyte": ("b", 1), "char": ("B", 1),
    "short": ("h", 2), "ushort": ("H", 2),
    "int": ("i", 4), "uint": ("I", 4),
    "long": ("q", 8), "ulong": ("Q", 8),
    "float": ("f", 4), "double": ("d", 8),
}


class Reader:
    def __init__(self, data):
        self.d = data
        self.o = 0

    def _take(self, n):
        if self.o + n > len(self.d):
            raise EOFError(f"need {n} at off {self.o}, have {len(self.d)-self.o}")
        v = self.d[self.o:self.o + n]; self.o += n; return v

    def prim(self, t):
        f, n = PRIM[t]
        return struct.unpack(ENDIAN + f, self._take(n))[0]

    def count(self):
        return struct.unpack(ENDIAN + COUNT_SIZE, self._take(struct.calcsize(COUNT_SIZE)))[0]

    def string(self):
        n = struct.unpack(ENDIAN + STR_LEN, self._take(struct.calcsize(STR_LEN)))[0]
        return self._take(n).decode("utf-8", "replace")


class Writer:
    def __init__(self):
        self.parts = []

    def prim(self, t, v):
        f, _ = PRIM[t]; self.parts.append(struct.pack(ENDIAN + f, v)); return self

    def count(self, n):
        self.parts.append(struct.pack(ENDIAN + COUNT_SIZE, n)); return self

    def string(self, s):
        b = (s or "").encode("utf-8")
        self.parts.append(struct.pack(ENDIAN + STR_LEN, len(b))); self.parts.append(b); return self

    def bytes(self):
        return b"".join(self.parts)


class Schema:
    def __init__(self, path=None):
        path = path or os.path.join(os.path.dirname(__file__), "..", "protocol", "messages.json")
        data = json.load(open(path, encoding="utf-8"))
        self.structs = {s["name"]: s["fields"] for s in data["structs"]}
        self.by_name = {m["name"]: m for m in data["messages"]}
        self.by_id = {m["msg_id"]: m for m in data["messages"] if m["msg_id"] is not None}

    # ---- type-directed value codec ----
    def _read(self, r, typ):
        if typ.endswith("[]"):
            base = typ[:-2]; n = r.count()
            return [self._read(r, base) for _ in range(n)]
        if typ.startswith("Pair<"):
            base = typ[5:-1]; return [self._read(r, base) for _ in range(2)]
        if typ.startswith("Ternary<"):
            base = typ[8:-1]; return [self._read(r, base) for _ in range(3)]
        if typ in PRIM:
            return r.prim(typ)
        if typ == "string":
            return r.string()
        if typ in self.structs:
            return {f["name"]: self._read(r, f["type"]) for f in self.structs[typ]}
        raise NotImplementedError(f"type {typ!r} (e.g. polymorphic 'object') not handled")

    def _write(self, w, typ, val):
        if typ.endswith("[]"):
            base = typ[:-2]; w.count(len(val))
            for x in val:
                self._write(w, base, x)
            return
        if typ.startswith("Pair<") or typ.startswith("Ternary<"):
            base = typ[typ.index("<") + 1:-1]
            for x in val:
                self._write(w, base, x)
            return
        if typ in PRIM:
            w.prim(typ, val); return
        if typ == "string":
            w.string(val); return
        if typ in self.structs:
            for f in self.structs[typ]:
                self._write(w, f["type"], val[f["name"]])
            return
        raise NotImplementedError(f"type {typ!r} not handled")

    # ---- message body ----
    def decode_body(self, name_or_id, body):
        m = self.by_id[name_or_id] if isinstance(name_or_id, int) else self.by_name[name_or_id]
        r = Reader(body)
        out = {f["name"]: self._read(r, f["type"]) for f in m["fields"]}
        return m["name"], out

    def encode_body(self, name, values):
        m = self.by_name[name]
        w = Writer()
        for f in m["fields"]:
            self._write(w, f["type"], values.get(f["name"]))
        return w.bytes()

    # ---- framing ----
    def frame(self, name_or_id, values=None):
        m = self.by_id[name_or_id] if isinstance(name_or_id, int) else self.by_name[name_or_id]
        body = self.encode_body(m["name"], values or {})
        msgid = struct.pack(ENDIAN + FRAME_MSGID, m["msg_id"])
        total = len(body) + len(msgid) + struct.calcsize(FRAME_LEN)
        ln = total if FRAME_LEN_INCLUSIVE else len(body) + len(msgid)
        return struct.pack(ENDIAN + FRAME_LEN, ln) + msgid + body

    def read_frames(self, buf):
        """Yield (msgid, name, body, consumed_total). Stops at a partial frame."""
        frames, off = [], 0
        lw = struct.calcsize(FRAME_LEN); mw = struct.calcsize(FRAME_MSGID)
        while len(buf) - off >= lw + mw:
            ln = struct.unpack_from(ENDIAN + FRAME_LEN, buf, off)[0]
            total = ln if FRAME_LEN_INCLUSIVE else ln + lw
            if total < lw + mw or off + total > len(buf):
                break
            msgid = struct.unpack_from(ENDIAN + FRAME_MSGID, buf, off + lw)[0]
            body = buf[off + lw + mw: off + total]
            m = self.by_id.get(msgid)
            frames.append((msgid, m["name"] if m else "??", body))
            off += total
        return frames, off


def _parse(buf, endian, lenfmt, midfmt, inclusive, names):
    frames, off, known = [], 0, 0
    lw, mw = struct.calcsize(lenfmt), struct.calcsize(midfmt)
    while len(buf) - off >= lw + mw:
        ln = struct.unpack_from(endian + lenfmt, buf, off)[0]
        total = ln if inclusive else ln + lw
        if total < lw + mw or off + total > len(buf):
            break
        mid = struct.unpack_from(endian + midfmt, buf, off + lw)[0]
        body = buf[off + lw + mw: off + total]
        nm = names.get(mid)
        known += 1 if nm else 0
        frames.append((mid, nm or "??", body))
        off += total
    return frames, off, known


def detect_framing(buf, names):
    """Brute-force the header layout from real bytes. Returns best dict or None.
    None / known==0 across all combos strongly implies the stream is ENCRYPTED."""
    best = None
    for endian in ("<", ">"):
        for lenfmt in ("H", "I"):
            for midfmt in ("I", "H"):
                for inclusive in (True, False):
                    frames, off, known = _parse(buf, endian, lenfmt, midfmt, inclusive, names)
                    if not frames:
                        continue
                    score = (known, off)               # most known ids, then bytes consumed
                    if best is None or score > best["score"]:
                        best = dict(score=score, endian=endian, lenfmt=lenfmt,
                                    midfmt=midfmt, inclusive=inclusive,
                                    frames=frames, consumed=off, known=known)
    return best


def apply_framing(cfg):
    """Lock in a detected framing so the Schema/frame/read_frames use it."""
    global ENDIAN, FRAME_LEN, FRAME_MSGID, FRAME_LEN_INCLUSIVE
    ENDIAN = cfg["endian"]; FRAME_LEN = cfg["lenfmt"]
    FRAME_MSGID = cfg["midfmt"]; FRAME_LEN_INCLUSIVE = cfg["inclusive"]


if __name__ == "__main__":
    # round-trip self-test across primitives, strings, arrays, and nested structs
    s = Schema()
    cases = {
        "server_version_s2c": {"v": "2.0.1.4"},
        "batch_delete_item_s2c": {"itemids": [1, 2, 9999999999], "reason": 7},
        "tcp_connect_c2s": {"conn_type": 1, "roleid": 123456789, "account": "guest_1",
                             "key": "k", "sign": "s", "sn": 42},
        "player_role_list_s2c": {"roles": []},
        "create_role_request_c2s": {"name": "Hero", "classtype": 3},
    }
    ok = 0
    for name, vals in cases.items():
        body = s.encode_body(name, vals)
        rname, decoded = s.decode_body(name, body)
        match = decoded == vals
        ok += match
        print(f"  {'OK ' if match else 'FAIL'} {name:<24} {len(body):>3}B  {decoded}")
    # framing round-trip
    fr = s.frame("heart_beat_s2c", {"time": 1000, "stime": 2000})
    frames, consumed = s.read_frames(fr + fr)
    print(f"  frame: {fr.hex()}  -> read {len(frames)} frames, consumed {consumed}/{len(fr)*2}")
    print(f"SELFTEST: {ok}/{len(cases)} body round-trips OK"
          + ("" if ok == len(cases) else "  <-- CHECK"))
