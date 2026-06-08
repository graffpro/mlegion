<#  Align + re-sign the repackaged APK, then (re)install it into LDPlayer via ldconsole.  #>
$ErrorActionPreference = "Stop"
$repo  = Split-Path $PSScriptRoot -Parent
$build = Join-Path $repo "build"
$unsigned = Join-Path $build "ml_repacked_unsigned.apk"
$java  = Get-ChildItem (Join-Path $PSScriptRoot "jdk") -Recurse -Filter java.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
$signer = Join-Path $PSScriptRoot "uber-apk-signer.jar"
$ld = "D:\LDPlayer\LDPlayer9\ldconsole.exe"

if (-not $java)   { throw "java.exe not found under tools\jdk (JDK still downloading?)" }
if (-not (Test-Path $signer))   { throw "uber-apk-signer.jar missing" }
if (-not (Test-Path $unsigned)) { throw "run repackage_apk.py first" }

Write-Host "== signing (align + v1/v2) ==" -ForegroundColor Cyan
& $java -jar $signer --apks $unsigned --allowResign --overwrite 2>&1 | Out-Host
$signed = Get-ChildItem $build -Filter *Signed*.apk -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $signed) { $signed = $unsigned }   # --overwrite replaces in place
Write-Host "signed APK: $signed" -ForegroundColor Green

Write-Host "== reinstalling into LDPlayer ==" -ForegroundColor Cyan
& $ld uninstallapp --index 0 --packagename com.xgg.ml 2>&1 | Out-Host
Start-Sleep 2
& $ld installapp --index 0 --filename "$signed" 2>&1 | Out-Host
Write-Host "install exit: $LASTEXITCODE" -ForegroundColor Green
Write-Host "DONE. Next: start server (portal+gate), then ldconsole runapp com.xgg.ml" -ForegroundColor Green
