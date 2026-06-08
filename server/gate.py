"""
Magic Legion — TCP game gate (Phase 2/3).

CURRENTLY A SNIFFER. Accepts the client's connection, hex-logs every byte, and tries to
frame packets as [u16 length][u32 msgid][body], labelling the msgid via the extracted
protocol schema. This confirms the wire format from the client's REAL first packets
(server_version_c2s=2, tcp_connect_c2s=42, ...). Handshake responses are added in Phase 3
once framing + encryption are confirmed from these captures.

Run:  python server/gate.py
"""
import asyncio, struct, datetime
import config

NAMES = config.load_msgid_names()


def hexdump(b, width=16):
    out = []
    for i in range(0, len(b), width):
        chunk = b[i:i + width]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asci = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        out.append(f"    {i:04x}  {hexs:<{width*3}}  {asci}")
    return "\n".join(out)


def try_frame(buf):
    """Best-guess framing [u16 len][u32 msgid]. Returns (frames, bytes_consumed).
    We try this hypothesis live; if msgids don't resolve to known names, the real
    framing differs and we adjust from the capture."""
    frames, off = [], 0
    while len(buf) - off >= 6:
        ln = struct.unpack_from("<H", buf, off)[0]          # u16 LE total length
        if ln < 6 or off + ln > len(buf):
            break
        msgid = struct.unpack_from("<I", buf, off + 2)[0]   # u32 LE msgid
        body = buf[off + 6: off + ln]
        frames.append((msgid, NAMES.get(msgid, "??UNKNOWN??"), body))
        off += ln
    return frames, off


async def handle(reader, writer):
    peer = writer.get_extra_info("peername")
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] ==================== GATE connection from {peer} ====================")
    buf = b""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buf += data
            print(f"[{peer[0]}] +{len(data)} bytes (buffer={len(buf)}):")
            print(hexdump(data))
            frames, consumed = try_frame(buf)
            for msgid, name, body in frames:
                print(f"    >> FRAME  msgid={msgid:<5} {name:<32} bodylen={len(body)}")
            if consumed:
                buf = buf[consumed:]
            # Phase 3 TODO: dispatch frames -> send handshake responses.
    except Exception as e:
        print(f"[{peer[0]}] read error: {e}")
    finally:
        print(f"[{peer}] ==================== disconnected ====================")
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", config.GATE_PORT)
    print(f"[gate] sniffer listening on 0.0.0.0:{config.GATE_PORT}")
    print(f"[gate] loaded {len(NAMES)} msgid names from the protocol schema")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[gate] stopped")
