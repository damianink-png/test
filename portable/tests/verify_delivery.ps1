param([string]$Launcher,[string]$Output)
$ErrorActionPreference='Stop'
$clock=[Diagnostics.Stopwatch]::StartNew()
$p=Start-Process -FilePath $Launcher -ArgumentList '--verify-only' -Wait -PassThru
if($p.ExitCode -ne 0){throw 'Portable manifest verification failed'}
$cold=$clock.Elapsed.TotalSeconds;$clock.Restart()
$p=Start-Process -FilePath $Launcher -ArgumentList '--verify-only' -Wait -PassThru
if($p.ExitCode -ne 0){throw 'Warm portable verification failed'}
$warm=$clock.Elapsed.TotalSeconds;$clock.Restart()
$p=Start-Process -FilePath $Launcher -ArgumentList '--gui-smoke' -PassThru
if(-not $p.WaitForExit(120000)){Stop-Process -Id $p.Id -Force;throw 'Portable GUI did not confirm startup'}
if($p.ExitCode -ne 0){throw 'Portable GUI readiness failed'}
$gui=$clock.Elapsed.TotalSeconds
New-Item -ItemType Directory -Path $Output -Force | Out-Null
@{launcher=$Launcher;cold_verify_seconds=$cold;warm_verify_seconds=$warm;gui_seconds=$gui;result='PASS'}|ConvertTo-Json|Set-Content -Encoding utf8 (Join-Path $Output 'startup-result.json')
Write-Host "PORTABLE_GUI_AND_CACHE_PASS cold=$cold warm=$warm gui=$gui"
