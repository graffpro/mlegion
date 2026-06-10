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

## Phase 3 — TCP login gateway (the first big milestone)  ✅ DONE
_`server/handshake.py` drives connect→auth→roles→join→init→world; `server/test_login.py` proves it
over a real TCP socket. **Framing CONFIRMED from a live exchange** (LE / u16 length / u32 msgid /
length-inclusive — the gate auto-detects it); the handshake is NOT encrypted for our flow, so
`ML_RESPOND=1` drives login→world directly. No Ghidra/`needKey` work was needed._
Get from TCP connect all the way into the game world with a character.
- [ ] TCP listener speaking CBNetLib framing + heartbeat + serial numbers.
- [ ] Handle the connect handshake (`tcp_connect_success`, `serial_number`).
- [ ] Implement encryption (`needKey`) once confirmed.
- [ ] Login `*_c2s` → role list / create-role → enter-world `*_s2c` with a seed player.
- [ ] Send the minimum `s2c` snapshot the client needs to render the main town.

**Deliverable:** you log in and see your hero / main scene served entirely by us.

## Phase 4 — In-world gameplay  ✅ DONE (stateful)
_`server/handshake.py` now streams the **full init flood (113 modules)** and runs a **stateful**
session: `role_move` commits the player's position, `server_battle_create` wins → `role_levelup`,
plus name-check / reliability / exit-logout. `server/test_login.py` walks login→world→play (walk →
battle → walk) = **14/14 checkpoints**, verified on the inline brain AND the live gate. `python run.py`
is a one-click demo of the whole thing._

## Phase 4+ — remaining game systems (ceiling reached)
The deeper systems (bag/heroes/attributes/full battles/shop/gacha/arena/guild) ride on
`kvobject{uint key, object value}` messages whose **polymorphic value type can only be confirmed
from a LIVE client packet** — and the original client is **unrenderable** (see Outcome), so there is
no client to capture from. The codec (`server/codec.py`) handles everything except this polymorphic
`object`; that is the single remaining gap, and it is gated on the lost client, not on effort.

---

## Outcome — where the revival lands
- **Server: revived & proven.** Login → enter world → stateful in-world play, all served by us and
  asserted end-to-end. This is the real, durable deliverable.
- **Original client: runs on our build but cannot render.** It's a *thin* client — ~79% of its assets
  (all 233 proto data tables + most UI art) lived only on the dead CDN and are gone. We made it take
  100% from our build (0 downloads, 8 loading blockers cleared via `tools/repackage_apk.py` +
  `tools/fill_placeholders.py` + UnityPy), but structured **data cannot be faked** — it stalls at
  "data init". So the client is a proven *transport* for the server, not a playable UI.

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
