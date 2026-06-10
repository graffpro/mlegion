# Magic Legion private server

Stdlib-only Python (no pip installs) — the recovered protocol in `../protocol/messages.json` is all
it needs. Drives a client from TCP connect into the game world and through a stateful play session.

| File | Role |
|------|------|
| `codec.py` | wire codec — encodes/decodes the body of any of the 1630 `cb_net` messages + frames them `[u16 len][u32 msgid][body]` (LE, length-inclusive). Self-test: `python codec.py`. |
| `handshake.py` | the **game logic** — turns each incoming `*_c2s` into the `*_s2c` reply(s): connect → auth → role list → join → init flood (113 modules) → enter world → in-world play (move/battle/level-up/…). Stateful `Session`. |
| `gate.py` | TCP game gate — auto-detects the wire framing from the first packet, then (with `ML_RESPOND=1`) drives the session via `handshake.handle`. Sniffer-only without it. |
| `portal.py` | HTTP portal — emulates `*.ml.fragon.com` (version, serverlist, `getgatev2`, login, CDN). Hands the client our gate via `svrip`/`svrport`. |
| `config.py` | host IP, bind/advertised ports, the advertised server entry. |
| `test_login.py` | end-to-end proof — a test client over a real socket: login → world → walk → battle → walk → 14/14 checkpoints + 113 modules. |

## Prove it works
```bash
python test_login.py          # inline brain + client, one process
# or against the deployable gate process:
ML_RESPOND=1 ML_GATE_BIND=9102 python gate.py        # terminal A
ML_GATE=127.0.0.1:9102 python test_login.py          # terminal B
# or one-click from the repo root:
python ../run.py
```

## Run the full stack (to point a real client at it)
```bash
ML_HOST_IP=127.0.0.1 python portal.py     # terminal 1 — HTTP (ports 9004, 80)
ML_HOST_IP=127.0.0.1 ML_RESPOND=1 python gate.py   # terminal 2 — TCP gate (9100)
```
Env knobs: `ML_RESPOND=1` (gate drives login vs sniff-only), `ML_PORTAL_BIND`/`ML_GATE_BIND` (bind
elsewhere and `adb reverse` the guest's advertised ports onto them), `ML_HOST_IP` (advertised gate IP).

Redirect the client to us by repackaging `assets/config.ini`'s hosts to our box (see
`../tools/repackage_apk.py`) or hosts/DNS-redirecting `*.ml.fragon.com`. See `SETUP_EMULATOR.md`.

## Wire format — confirmed
The gate brute-forces the header from the client's first packet and locked it in from a live
exchange: **little-endian, u16 length, u32 msgid, length-inclusive**, strings length-prefixed (u16),
lists count-prefixed. The login/play handshake is **not encrypted** for our flow. The one remaining
codec gap is the polymorphic `kvobject{key, object}` value, whose typing needs a live client capture.
