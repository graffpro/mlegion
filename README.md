# mlegion — *Magic Legion: Hero Legend* server revival

Open reverse-engineering & private-server emulator for the **defunct** mobile game
*Magic Legion – Hero Legend* (`com.xgg.ml`), so the original client can be played again
after the official servers were shut down (final client **2.0.1.4**, 2020).

> ⚠️ **Preservation project.** Uses only the player's own client copy. **No copyrighted
> client material is stored here** — the APK, Unity assets, `libil2cpp.so`,
> `global-metadata.dat`, and the raw Il2CppDumper output are git-ignored. This repo holds
> only original analysis tooling, the recovered protocol schema, documentation, and server code.

## Status
- [x] **Phase 0** — Recon (engine, endpoints, protocol structure)
- [x] **Phase 1** — Protocol extraction → `protocol/messages.json` (**1630** messages)
- [ ] **Phase 2** — HTTP portal server (version / serverlist / `getgatev2`)
- [ ] **Phase 3** — TCP game gate: handshake → login → enter world
- [ ] **Phase 4** — Game systems, incrementally

## What we know
- **Engine:** Unity **IL2CPP** (global-metadata v24, unencrypted → fully recoverable).
- **Backend:** an HTTP *portal* (`*.ml.fragon.com:9004`, `/api/channel|center/*`,
  `getgatev2` hands out the realtime gate) + a custom **TCP binary protocol**
  (`cb_net` / CBNetLib): `base_message`(uint msgid) + `PacketStream` codec, two
  connections (normal + PvP), 30 s heartbeat, `needKey` (RC4-like) encryption.
- **1630 messages** (501 c2s / 1129 s2c) + 164 structs recovered. Login/enter-world flow
  fully mapped. See **`FINDINGS.md`**, **`ROADMAP.md`**, **`protocol/LOGIN_FLOW.md`**.
- No prior private-server/emulator exists for this title — built from zero.

## Layout
| Path | Contents |
|------|----------|
| `tools/` | protocol extractor & query scripts (Python) |
| `protocol/` | recovered schema (`messages.json`), `LOGIN_FLOW.md`, `fieldtypes.json` |
| `analysis/` | analysis scripts (their large outputs are git-ignored) |
| `server/` | the emulator: HTTP portal + TCP game gate *(WIP)* |
| `FINDINGS.md`, `ROADMAP.md` | what we found / how we're building it |

## Reproduce the schema
Provide your own `com.xgg.ml` 2.0.1.4 APK, run [Il2CppDumper](https://github.com/Perfare/Il2CppDumper)
on its `libil2cpp.so` + `global-metadata.dat`, then `python tools/extract_protocol.py`
to regenerate `protocol/messages.json` from the resulting `dump.cs`.

## Legal
Interoperability/preservation work on a discontinued, delisted title. Do not redistribute the
publisher's APK or assets.
