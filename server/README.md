# Magic Legion private server (WIP)

Two processes, stdlib-only Python (no pip installs):

| File | Role |
|------|------|
| `portal.py` | HTTP portal — emulates `*.ml.fragon.com` (version, serverlist, `getgatev2`, login). Hands the client our gate. |
| `gate.py` | TCP game gate — **currently a sniffer**: hex-logs the client's packets and labels them by `msgid` from `../protocol/messages.json`. |
| `config.py` | host IP, ports, advertised server entry. |

## Run
```powershell
# set the IP the emulator will reach this PC on (your Windows LAN IP)
$env:ML_HOST_IP = "192.168.50.180"
python server/portal.py     # terminal 1  (ports 9004, 443, 80)
python server/gate.py       # terminal 2  (port 9100)
```

## Redirect the client to us (done once the emulator is up)
On the rooted emulator, point the game's hosts at this PC:
```
192.168.50.180  android.ml.fragon.com
192.168.50.180  account.ml.fragon.com
192.168.50.180  push.ml.fragon.com
```
(edit `/system/etc/hosts` via adb with root, or a root file manager.)

## What we're capturing
The client's first TCP packets to the gate (`server_version_c2s`=2, `tcp_connect_c2s`=42…)
confirm the exact wire framing, endianness, and whether the handshake is encrypted. The
sniffer's `try_frame()` assumes `[u16 len][u32 msgid]` — if the labelled msgids look right,
the hypothesis holds; if not, we adjust from the hexdump.

> Note: portal JSON shapes and TLS handling are first-pass and will be refined from the
> client's real behavior (watch the `UNHANDLED` lines + Android `logcat`).
