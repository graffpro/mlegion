# Magic Legion — Server Revival Roadmap

Goal: bring the dead `com.xgg.ml` game back online by reimplementing its backend
(private-server emulator) and pointing the original client at it.

This is **incremental**. Each phase is a usable milestone. We do NOT try to rebuild
the whole game at once — we get the client to connect, then log in, then enter the
world, then add systems one opcode at a time.

---

## Phase 0 — Recon ✅ DONE
Engine, endpoints, protocol structure, codec all identified. See `FINDINGS.md`.

## Phase 1 — Protocol extraction (foundation)  ✅ DONE
_1630 messages → `protocol/messages.json`; `server/codec.py` encodes/decodes any of them
(round-trip 5/5); framing auto-detected by the sniffer instead of via Ghidra._
Turn the 1,630 `base_message` classes in `dump.cs` into a machine-readable schema and
a working codec, so the server can speak the exact wire format.
- [ ] `tools/extract_protocol.py` — parse `dump.cs`: for every `: base_message`, capture
      class name, `MSG_ID`, ordered fields (name + type) → `protocol/messages.json`.
- [ ] Confirm framing/header + endianness from `CSocket` encode path (Ghidra + `script.json`).
- [ ] Resolve nested struct types (`sitem`, `Pair<T>`, …) — parse their classes too.
- [ ] Codegen a Python (or Node) **PacketStream** codec + message (de)serializers.
- [ ] Unit test: round-trip encode→decode a handful of messages.

**Deliverable:** library that can read/write any of the 1,630 messages.

## Phase 2 — HTTP portal server  ✅ DONE (built + tested; awaiting live client)
_`server/portal.py` serves https (CA via `gen_certs.py`); `server/gate.py` smart sniffer;
`SETUP_EMULATOR.md` + `tools/device_setup.ps1` provision the emulator._
Implement the `/api/channel/*` + `/api/center/*` endpoints so the client passes the
update/login/server-select screens and asks us for a game gateway.
- [ ] Static `version/show`, `notice/show`, feature `gameswitch/*` switches.
- [ ] `serverlist/show` + `serverlistwithrole/show` → advertise one server.
- [ ] `getgatev2` → return **our** TCP gateway ip:port.
- [ ] Account/auth stub on `account.ml.fragon.com` (guest login first).

**Deliverable:** client boots, updates clean, shows our server in the list.
**Test gate:** redirect `*.ml.fragon.com` → our box (hosts file / DNS).

## Phase 3 — TCP login gateway (the first big milestone)  🟡 DRAFT
_`server/handshake.py` drives connect→auth→roles→join→init→world; integration-tested against
a simulated client (13 responses). Blocked on a live capture to confirm framing + whether the
handshake is encrypted, then flip `ML_RESPOND=1`._
Get from TCP connect all the way into the game world with a character.
- [ ] TCP listener speaking CBNetLib framing + heartbeat + serial numbers.
- [ ] Handle the connect handshake (`tcp_connect_success`, `serial_number`).
- [ ] Implement encryption (`needKey`) once confirmed.
- [ ] Login `*_c2s` → role list / create-role → enter-world `*_s2c` with a seed player.
- [ ] Send the minimum `s2c` snapshot the client needs to render the main town.

**Deliverable:** you log in and see your hero / main scene served entirely by us.

## Phase 4+ — Game systems, incrementally
Implement handlers opcode-by-opcode, by gameplay area, each independently testable:
heroes & bag → battle/stage → shop/gacha → arena (PvP server) → guild → mail → events.
Drive priority by what the client requests on each screen (log unknown opcodes).

---

## Testing methodology
- **Client runner:** Android emulator with ARM support, or a real Android device
  (APK is arm64-v8a/armeabi-v7a). Bluestacks/LDPlayer/Android Studio AVD or device.
- **Redirect to our server:** override the config hosts — either edit `assets/config.ini`
  and repackage+resign the APK, or DNS/hosts-redirect `*.ml.fragon.com` (root device or
  emulator `/etc/hosts`, or a local DNS like dnsmasq / Acrylic).
- **Observe:** server-side log of every received `msgId` (named via our schema) tells us
  exactly what the client wants next — this is the loop that drives Phase 4.

## Server stack (proposed)
- Language: **Python** (asyncio) for speed of iteration, or **Node.js**. Either can do the
  TCP gateway + HTTP portal. Swap to Go/C# later if perf matters.
- One process for HTTP portal, one asyncio TCP server for the game gate (+ later PvP gate).
- Storage: SQLite/JSON to start (single-player revival); Postgres if multi-user.

## Realistic scope
- Phases 1–3 (connect → log in → see the world) = the achievable, high-value core.
- Phase 4 = open-ended; a faithful full revival is a large, ongoing effort. We grow it
  system by system; even a partial revival is playable and a real achievement.

## Legal note
Game-preservation / private-server work on a defunct, delisted title. We use only the
user's own copy of the client. Don't redistribute the publisher's assets/APK.
