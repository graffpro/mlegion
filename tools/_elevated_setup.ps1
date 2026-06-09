# ELEVATED (admin) one-shot: disable the Windows hypervisor / VBS (so LDPlayer's VM gets
# native VT-x = fast), and schedule the client bring-up to auto-run after the reboot.
# Writes a result marker the non-elevated side polls to confirm the UAC was approved.
$log = "C:\Users\NoteBook\Documents\magic-legion\server\_elevated_done.txt"
"ML elevated setup started $(Get-Date)" | Set-Content $log
& bcdedit /set hypervisorlaunchtype off 2>&1 | Add-Content $log
& reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity" /v Enabled /t REG_DWORD /d 0 /f 2>&1 | Add-Content $log
& schtasks /create /tn "ML_BringUp" /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"C:\Users\NoteBook\Documents\magic-legion\tools\_post_reboot.ps1`"" /sc onlogon /rl highest /f 2>&1 | Add-Content $log
"--- hypervisorlaunchtype ---" | Add-Content $log
& bcdedit /enum "{current}" 2>&1 | Select-String -Pattern "hypervisorlaunchtype" | Add-Content $log
"--- scheduled task ---" | Add-Content $log
& schtasks /query /tn "ML_BringUp" /fo LIST 2>&1 | Select-String -Pattern "TaskName|Status|Next" | Add-Content $log
"DONE" | Add-Content $log
