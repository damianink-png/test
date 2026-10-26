param([string]$OutputDirectory = "diagnostics")
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$absolute = (Resolve-Path $OutputDirectory).Path
$dump = Join-Path $absolute "crash_dumps"
New-Item -ItemType Directory -Force -Path $dump | Out-Null
$reg = 'HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\DSCompare.exe'
New-Item -Path $reg -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpFolder -Value $dump -PropertyType ExpandString -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpType -Value 2 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpCount -Value 3 -PropertyType DWord -Force | Out-Null
$env:PYTHONFAULTHANDLER = '1'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONUTF8 = '1'
"TimestampUTC=$((Get-Date).ToUniversalTime().ToString('o'))" | Out-File (Join-Path $absolute 'environment.txt') -Encoding utf8
"Computer=$env:COMPUTERNAME; PID=$PID; OS=$([Environment]::OSVersion.VersionString)" | Add-Content (Join-Path $absolute 'environment.txt')
Get-ComputerInfo | Select-Object OsName,OsVersion,OsArchitecture,WindowsVersion | Format-List | Out-File (Join-Path $absolute 'computer.txt')
Write-Host "Windows Error Reporting full crash dumps configured: $dump"
