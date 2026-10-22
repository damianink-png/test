param([switch]$NoInstall, [switch]$InstallOnly)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.\DSCompareV3.py')) { throw 'Brak DSCompareV3.py' }
if (-not $NoInstall) {
  python -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw 'Pip upgrade failed' }
  python -m pip install -r requirements.txt 'PySide6==6.8.3' 'vtk>=9.6,<9.7' 'cadquery-ocp==7.9.3.1.1' 'cadquery-ocp-proxy==7.9.3.1.1' 'pyinstaller>=6.11,<7'
  if ($LASTEXITCODE -ne 0) { throw 'Dependencies failed' }
  python -m pip check
  if ($LASTEXITCODE -ne 0) { throw 'Inconsistent dependencies' }
}
if ($InstallOnly) { return }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DSCompare --icon assets/DSCompare.ico --collect-all OCP --hidden-import dsac29.parallel_import --hidden-import dsac29.icons_r119 --hidden-import dsac29.z3_support --hidden-import dsac29.import_cache --hidden-import dsac29.gui_modern --hidden-import dsac29.zw3d_launcher --hidden-import dsac29.mass_batch --hidden-import dsac29.mass_drop --hidden-import dsac29.step_diagnostics --hidden-import dsac29.local_tests --hidden-import dsac29.registration_gate --add-data "build_info.json;." --add-data "dsac29/preview_template.html;dsac29" --hidden-import dsac29.preview3d --add-data "assets/DSCompare.ico;assets" --add-data "assets/DSCompare.png;assets" --distpath "dist" DSCompareV3.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
if (-not (Test-Path '.\dist\DSCompare\DSCompare.exe')) { throw 'No EXE created' }
Write-Host "Gotowe: $PSScriptRoot\dist\DSCompare\DSCompare.exe"
