$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'DSCompareV3.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Nie znaleziono DSCompareV3.exe obok skryptu: $exe" }
$folder = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$lnk = Join-Path $folder 'DS Compare.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnk)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$exe,0"
$shortcut.Description = 'DS Compare - Geometry & Assembly Comparison'
$shortcut.Save()
Write-Host "Utworzono skrot w menu Start: $lnk"
Write-Host 'Aby przypiac aplikacje do paska zadan, uruchom ja i wybierz Przypnij do paska zadan.'
