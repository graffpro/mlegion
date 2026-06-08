"""
Magic Legion — TCP game gate (Phase 2/3).

CURRENTLY A SMART SNIFFER. Accepts the client's connection, hex-logs every byte, then
uses codec.detect_framing() to brute-force the header layout from the REAL bytes
(endian × len-width × msgid-width × inclusive), labels each packet by msgid, and
best-effort decodes the body via the extracted schema.

  * If known msgids resolve  -> we've confirmed the wire format; bodies decode.
  * If nothing resolves       -> the handshake is ENCRYPTED (needKey) or the header is
                                 exotic; the hexdump is what we then analyse.

Handshake RESPONSES (Phase 3) get wired in here once the above is confirmed.

Run:  python server/gate.py
"""
import asyncio, datetime, struct
import config, codec

SCHEMA = codec.Schema()
NAMES = {mid: m["name"] for mid, m in SCHEMA.by_id.items()}


def hexdump(b, width=16):
    out = []
    for i in range(0, len(b), width):
        chunk = b[i:i + width]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asci = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        out.append(f"    {i:04x}  {hexs:<{width*3}}  {asci}")
    return "\n".join(out)


async def handle(reader, writer):
    peer = writer.get_extra_info("peername")
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] ================= GATE connection from {peer} =================")
    buf = b""
    shown = None
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buf += data
            print(f"[{peer[0]}] +{len(data)} bytes (buffer={len(buf)}):")
            print(hexdump(data))

            best = codec.detect_framing(buf, NAMES)
            if best and best["known"]:
                sig = (best["endian"], best["lenfmt"], best["midfmt"], best["inclusive"])
                if sig != shown:
                    shown = sig
                    codec.apply_framing(best)
                    end = "LE" if best["endian"] == "<" else "BE"
                    print(f"    *** DETECTED FRAMING: {end}, len=u{8*struct.calcsize(best['lenfmt'])}"
                          f", msgid=u{8*struct.calcsize(best['midfmt'])}"
                          f", len_inclusive={best['inclusive']}  (known msgids={best['known']}) ***")
                frames, consumed = SCHEMA.read_frames(buf)
                for mid, name, body in frames:
                    line = f"    >> msgid={mid:<5} {name:<30} bodylen={len(body)}"
                    try:
                        _, fields = SCHEMA.decode_body(mid, body)
                        line += f"  {fields}"
                    except Exception as e:
                        line += f"  (body: {e})"
                    print(line)
                buf = buf[consumed:]
            else:
                print("    !! no known msgid under any framing hypothesis "
                      "-> stream likely ENCRYPTED (needKey) or exotic header; analyse hex above")
            # Phase 3 TODO: dispatch frames -> writer.write(SCHEMA.frame(resp, {...}))
    except Exception as e:
        print(f"[{peer[0]}] read error: {e}")
    finally:
        print(f"[{peer}] ================= disconnected =================")
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", config.GATE_PORT)
    print(f"[gate] smart sniffer listening on 0.0.0.0:{config.GATE_PORT}")
    print(f"[gate] loaded {len(NAMES)} msgid names; will auto-detect framing from first packet")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[gate] stopped")
