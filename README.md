# mlegion — *Magic Legion: Hero Legend* server revival

A from-scratch reverse-engineering project and working **private-server emulator** for the
**defunct** mobile game *Magic Legion – Hero Legend* (`com.xgg.ml`, final client **2.0.1.4**,
2020). The official servers and CDN are permanently gone; this rebuilds the server side from
the client alone and proves it can drive a client from login into the game world.

> ⚠️ **Preservation project.** Uses only the player's own client copy. **No copyrighted client
> material is stored here** — the APK, Unity assets, `libil2cpp.so`, `global-metadata.dat`, and
> raw Il2CppDumper output are git-ignored. This repo holds only original analysis tooling, the
> recovered protocol schema, documentation, and server code.

## Status

- [x] **Phase 0** — Recon (engine, endpoints, protocol structure)
- [x] **Phase 1** — Protocol extraction → `protocol/messages.json` (**1630** messages, 164 structs)
- [x] **Phase 2** — HTTP portal (version / serverlist / `getgatev2`) — `server/portal.py`
- [x] **Phase 3** — TCP game gate: handshake → login → **enter world** — `server/gate.py` + `handshake.py`
- [x] **Phase 4** — Stateful in-world gameplay (full init flood, movement, battle, level-up)

**The revived server is proven end-to-end:** `python server/test_login.py` walks a client across
a real TCP socket through `login → enter world → in-world play` and asserts **14/14 checkpoints +
113 module-init messages** — against both the inline logic and the live gate (which auto-detects
the wire framing from the first packet).

## What was recovered

- **Engine:** Unity **IL2CPP** (global-metadata v24, unencrypted → fully recoverable). C# game logic.
- **Backend:** an HTTP *portal* (`*.ml.fragon.com:9004`, `/api/channel|center/*`; `getgatev2` hands
  out the realtime gate) + a custom **TCP binary protocol** (`cb_net`/CBNetLib): `base_message`(uint
  msgid) + a `PacketStream` codec, two connections (normal + PvP), 30 s heartbeat.
- **1630 messages** (501 c2s / 1129 s2c) + 164 structs, with the login→enter-world→play flow fully
  mapped (`protocol/LOGIN_FLOW.md`, `protocol/critical_path.txt`). **Wire format confirmed** from a
  live exchange: little-endian, u16 length, u32 msgid, length-inclusive.
- No prior private-server/emulator existed for this title — built from zero.

## Run it (the proof)

```bash
# 1) End-to-end proof — spins up the gate brain + a test client on a real socket and plays a session
python server/test_login.py
#    -> login -> world -> walk -> battle (+level) -> walk -> 14/14 checkpoints, 113 modules

# 2) Same, but against the *deployable* gate process (auto-detects framing from the first packet):
ML_RESPOND=1 ML_GATE_BIND=9102 python server/gate.py        # terminal A
ML_GATE=127.0.0.1:9102 python server/test_login.py          # terminal B
```

The full stack (for pointing a real client at it): run `server/portal.py` (HTTP, ports 9004/80) and
`server/gate.py` (TCP gate). `server/config.py` advertises the gate via `svrip`/`svrport`; the gate
runs as a sniffer until `ML_RESPOND=1`, then drives login→world via `handshake.py`. See
`server/README.md` and `server/SETUP_EMULATOR.md`.

## Live-client revival — how far it goes, and the wall

The original APK can be repackaged to take **everything from our build** (`tools/repackage_apk.py`,
`tools/fill_placeholders.py`): it parses our portal, passes version + the resource phase, and reaches
the **data-initialization** stage with **zero CDN downloads** — every one of its 1799 assets served
from our APK. Eight loading blockers were cleared along the way (cleartext HTTP, VBS throttling, NAT
via `adb reverse`, manifest surgery, Unity bundle collision / `.resS` / compatibility fixes via UnityPy).

**But the original client cannot be made to *render*.** It is a *thin* client: ~**79% of its assets
(1417 / 1799)**, including all 233 data tables (items, heroes, skills, localization) and most UI art,
lived only on the now-dead CDN. Art can be blanked with placeholders; **structured data cannot be
faked** — the client parses the 233 proto tables by name and uses them everywhere, so without the
real data it stalls at "data init". That data is gone. The **server** is therefore the revivable
deliverable; the original client provably runs on it but can't draw its screens.

## Layout

| Path | Contents |
|------|----------|
| `server/` | the emulator — `portal.py` (HTTP), `gate.py` (TCP gate), `handshake.py` (game logic), `codec.py` (wire codec), `test_login.py` (end-to-end proof) |
| `protocol/` | recovered schema — `messages.json` (1630 msgs), `LOGIN_FLOW.md`, `critical_path.txt`, `fieldtypes.json` |
| `tools/` | protocol extractor/query, APK repackager, placeholder/UnityPy asset tooling |
| `analysis/` | analysis scripts (their large outputs are git-ignored) |
| `FINDINGS.md`, `ROADMAP.md` | what we found / how it was built |

## Reproduce the schema

Provide your own `com.xgg.ml` 2.0.1.4 APK, run [Il2CppDumper](https://github.com/Perfare/Il2CppDumper)
on its `libil2cpp.so` + `global-metadata.dat`, then `python tools/extract_protocol.py` to regenerate
`protocol/messages.json` from the resulting `dump.cs`.

## Legal

Interoperability/preservation work on a discontinued, delisted title. Do not redistribute the
publisher's APK or assets.
