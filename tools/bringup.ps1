<#
  Full client bring-up. Run once the emulator is fast (VBS/hypervisor off + reboot).
  Order: start server -> wait emulator -> adb reverse -> (re)install -> launch -> watch handshake.
  Idempotent: safe to re-run.
#>
$ErrorActionPreference = "Continue"
$ws  = Split-Path $PSScriptRoot -Parent
$adb = "D:\LDPlayer\LDPlayer9\adb.exe"
$ld  = "D:\LDPlayer\LDPlayer9\ldconsole.exe"
$S   = "emulator-5554"
$env:ML_HOST_IP = "127.0.0.1"
$portal = "$ws\server\portal.log"; $gate = "$ws\server\gate.log"

Write-Host "[1/6] server (http portal 9004+80, gate sniffer 9100) ..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 9004,9100,80 -State Listen -EA SilentlyContinue |
  Select-Object -Expand OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -EA SilentlyContinue }
Start-Sleep 2
Start-Process python -ArgumentList "-u","server\gate.py"   -WorkingDirectory $ws -RedirectStandardOutput $gate   -RedirectStandardError "$ws\server\gate.err"   -WindowStyle Hidden
Start-Process python -ArgumentList "-u","server\portal.py" -WorkingDirectory $ws -RedirectStandardOutput $portal -RedirectStandardError "$ws\server\portal.err" -WindowStyle Hidden
Start-Sleep 4

Write-Host "[2/6] ensure emulator instance up + adb online ..." -ForegroundColor Cyan
& $ld launch --index 0 2>&1 | Out-Null
$online = $false
for ($i=0; $i -lt 60; $i++) {
  & $adb connect 127.0.0.1:5555 2>&1 | Out-Null
  if ((& $adb devices 2>&1) -match 'device$') { $online = $true; break }
  Start-Sleep 4
}
"adb online: $online"; & $adb devices 2>&1

Write-Host "[3/6] adb reverse (guest localhost -> host server) ..." -ForegroundColor Cyan
& $adb -s $S reverse --remove-all 2>&1 | Out-Null
& $adb -s $S reverse tcp:9004 tcp:9004 2>&1 | Out-Null
& $adb -s $S reverse tcp:9100 tcp:9100 2>&1 | Out-Null
& $adb -s $S reverse --list 2>&1

Write-Host "[4/6] (re)install repacked APK with all perms ..." -ForegroundColor Cyan
$apk = "$ws\build\ml_repacked_unsigned.apk"
if (Test-Path $apk) { & $adb -s $S install -r -g "$apk" 2>&1 | Select-Object -Last 1 } else { "!! build APK missing - run repackage_apk.py + sign" }

Write-Host "[5/6] launch game ..." -ForegroundColor Cyan
& $adb -s $S shell am force-stop com.xgg.ml 2>&1 | Out-Null; Start-Sleep 1
& $adb -s $S shell monkey -p com.xgg.ml -c android.intent.category.LAUNCHER 1 2>&1 | Out-Null

Write-Host "[6/6] watch portal + gate for the handshake (~4 min) ..." -ForegroundColor Cyan
for ($i=0; $i -lt 48; $i++) {
  $g = @(Get-Content $gate -EA SilentlyContinue | Where-Object { $_ -match 'connection from' })
  if ($g.Count) { Write-Host "*** GATE HANDSHAKE CAPTURED ***" -ForegroundColor Green; break }
  Start-Sleep 5
}
Write-Host "`n=== PORTAL ==="; Get-Content $portal -Tail 25 -EA SilentlyContinue
Write-Host "`n=== GATE ===";   Get-Content $gate   -Tail 90 -EA SilentlyContinue
Write-Host "`n(gate is in sniffer mode; once framing is confirmed, set ML_RESPOND=1 to drive login->world)"
