<#
  Provision a rooted LDPlayer/AVD to talk to our server:
  connect adb -> install APK -> trust our CA (system cert) -> redirect fragon hosts.

  Usage:
    $env:ML_HOST_IP = "192.168.50.180"
    tools\device_setup.ps1 -ApkPath "C:\path\to\Magic Legion ....apk"
#>
param(
  [string]$ApkPath = "C:\Users\NoteBook\Downloads\Magic Legion - Hero Legend_2.0.1.4_APKPure.apk",
  [string]$HostIp  = $env:ML_HOST_IP,
  [string]$AdbTarget = "127.0.0.1:5555"   # LDPlayer default; per-instance: 5557, 5559, ...
)
$ErrorActionPreference = "Continue"
if (-not $HostIp) { $HostIp = "192.168.50.180" }
$repo = Split-Path $PSScriptRoot -Parent
$adb  = Join-Path $PSScriptRoot "platform-tools\adb.exe"
if (-not (Test-Path $adb)) { Write-Host "adb missing at $adb"; exit 1 }

function Adb { & $adb @args 2>&1 | Out-Host }

Write-Host "== adb connect $AdbTarget ==" -ForegroundColor Cyan
Adb connect $AdbTarget
Adb devices

Write-Host "== root + remount /system (needs Root ON in LDPlayer) ==" -ForegroundColor Cyan
Adb root; Start-Sleep 1; Adb connect $AdbTarget
Adb remount
# fallback remount via su if 'adb remount' didn't take
& $adb shell "su -c 'mount -o rw,remount /system' 2>/dev/null; su -c 'mount -o rw,remount /' 2>/dev/null" 2>&1 | Out-Host

Write-Host "== install APK ==" -ForegroundColor Cyan
if (Test-Path $ApkPath) { Adb install -r -g "$ApkPath" } else { Write-Host "  APK not found: $ApkPath" -ForegroundColor Yellow }

Write-Host "== trust our CA as a SYSTEM cert ==" -ForegroundColor Cyan
$caFile = Get-ChildItem (Join-Path $repo "server\certs\android") -Filter *.0 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($caFile) {
  Adb push $caFile.FullName /system/etc/security/cacerts/
  Adb shell chmod 644 ("/system/etc/security/cacerts/" + $caFile.Name)
} else { Write-Host "  CA missing - run: python server\gen_certs.py" -ForegroundColor Yellow }

Write-Host "== redirect fragon hosts -> $HostIp ==" -ForegroundColor Cyan
$tmp = Join-Path $env:TEMP "ml_hosts"
@(
  "127.0.0.1   localhost"
  "::1         ip6-localhost"
  "$HostIp   android.ml.fragon.com"
  "$HostIp   android1.ml.fragon.com"
  "$HostIp   account.ml.fragon.com"
  "$HostIp   account1.ml.fragon.com"
  "$HostIp   push.ml.fragon.com"
  "$HostIp   translate.ml.fragon.com"
  "$HostIp   gmip.ml.fragon.com"
) -join "`n" | Set-Content -Encoding ASCII $tmp
Adb push $tmp /system/etc/hosts
Write-Host "-- /system/etc/hosts now: --"
Adb shell cat /system/etc/hosts

Write-Host "`nDONE." -ForegroundColor Green
Write-Host "Next: start server (python server\portal.py + python server\gate.py), launch the game,"
Write-Host "watch the GATE terminal for the handshake. Client-side log:"
Write-Host "  $adb logcat -v time | Select-String 'fragon|tcp|socket|connect|version'"
