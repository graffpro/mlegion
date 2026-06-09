# Runs ONCE at logon after the VBS-off reboot (scheduled by _elevated_setup.ps1).
# Brings the whole client up on our server, then removes its own scheduled task.
Start-Sleep -Seconds 45   # let Windows + LDPlayer services settle after boot
$tools = "C:\Users\NoteBook\Documents\magic-legion\tools"
try {
    & "$tools\bringup.ps1" *> "C:\Users\NoteBook\Documents\magic-legion\server\bringup_after_reboot.log" 2>&1
} catch {
    $_ | Out-File "C:\Users\NoteBook\Documents\magic-legion\server\bringup_after_reboot.log" -Append
}
schtasks /delete /tn "ML_BringUp" /f 2>&1 | Out-Null
