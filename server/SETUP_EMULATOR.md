# Connecting the client (emulator) to our server

Goal: redirect the game's `*.ml.fragon.com` calls to THIS PC, with our TLS CA trusted, so
the client passes the portal and connects to our gate — where we capture the handshake.

Prereqs: LDPlayer 9 (Android 9) with **Root ON** and **ADB enabled**
(Settings → Other settings). Our adb is at `tools/platform-tools/adb.exe`.
Host PC LAN IP = **192.168.50.180** (the emulator reaches us here).

## One-shot automation
```powershell
# 1) start the server (two terminals)
$env:ML_HOST_IP = "192.168.50.180"
python server/portal.py        # terminal A  (https 9004/443, http 80)
python server/gate.py          # terminal B  (tcp 9100 sniffer)

# 2) allow the emulator through Windows Firewall (admin PowerShell, once)
New-NetFirewallRule -DisplayName "ML server" -Direction Inbound -Action Allow `
  -Protocol TCP -LocalPort 80,443,9004,9100

# 3) provision the emulator (installs APK, trusts our CA, redirects hosts)
tools\device_setup.ps1 -ApkPath "C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk"
```

## What device_setup.ps1 does (manual equivalent)
```powershell
$adb = "tools\platform-tools\adb.exe"
& $adb connect 127.0.0.1:5555            # LDPlayer default (per-instance: 5557, 5559, ...)
& $adb root; & $adb remount               # needs Root ON
& $adb install -r -g $ApkPath             # install the game
# trust our CA as a SYSTEM cert:
& $adb push server\certs\android\b8c58d16.0 /system/etc/security/cacerts/
& $adb shell chmod 644 /system/etc/security/cacerts/b8c58d16.0
# redirect the fragon hosts to us:
& $adb push server\hosts /system/etc/hosts
& $adb shell cat /system/etc/hosts        # verify
```

## Capture
1. Launch **Magic Legion** in the emulator.
2. Watch **terminal A (portal)**: you should see `version/show`, `serverlist/show`,
   `getgatev2` hits → the redirect + TLS work.
3. Watch **terminal B (gate)**: when the client dials our gate, the sniffer prints the
   handshake. It auto-detects the framing and decodes bodies — or reports the stream looks
   ENCRYPTED. **This is the capture that unblocks Phase 3.**
4. Client-side view (errors, what host it dials):
   ```powershell
   tools\platform-tools\adb.exe logcat -v time | Select-String -Pattern "fragon|tcp|socket|connect|version|Unity"
   ```

## If the emulator can't reach 192.168.50.180
LDPlayer usually bridges to the LAN, so the PC LAN IP works. If not, find the alias the
emulator sees the host as (often the gateway), set `ML_HOST_IP` to it, re-run gen_certs.py
(so the cert SAN/IP matches) and device_setup.ps1.

## Notes
- TLS: the game (2017 Unity) should trust the system store; if it pins or ignores certs
  we'll see it in logcat and adapt (e.g. patch config.ini instead).
- The gate sniffer doesn't reply yet — it's capturing. Phase 3 wires in responses next.
```
