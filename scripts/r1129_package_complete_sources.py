"""Package the EXACT post-patch R11.29 source tree before PyInstaller.
Run in CI after all R11.29 patches/regressions and before the frozen build.
"""
from pathlib import Path
import os,sys,zipfile,hashlib,json
from datetime import datetime,timezone

root=Path(os.environ["DS_COMPARE_SOURCE"]).resolve()
workspace=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
dest=workspace/"DSCompare_R1129_PELNE_ZRODLA_PRZED_KOMPILACJA.zip"
prefix="DSCompare_R11.29_ZRODLA/"
exclude_dir={".git",".pytest_cache",".mypy_cache","__pycache__",".ruff_cache",
             ".venv","venv","dist","build","real_screenshots"}
exclude_ext={".pyc",".pyo",".tmp",".bak"}
expected=["DSCompareV3.py","requirements.txt","dsac29/gui_modern.py",
          "dsac29/alignment.py","dsac29/stage_fast.py","dsac29/cli.py",
          "dsac29/worker_v37.py","assets/DSCompare.ico",
          "dsac29/step_io.py","dsac29/report.py","VERSION.txt"]
for name in expected:
    if not (root/name).is_file():
        raise RuntimeError(f"Missing source file: {name}")
version=(root/"VERSION.txt").read_text(encoding="utf8").strip()
if version!="R11.29":
    raise RuntimeError(f"Wrong source snapshot version: {version!r}")

files=sorted(p for p in root.rglob("*") if p.is_file()
             and not any(part in exclude_dir for part in p.relative_to(root).parts)
             and p.suffix.lower() not in exclude_ext
             and p.name not in ("DSCompare.exe","DSCompare.spec")
             and p.stat().st_size < 80_000_000)
if len(files)<25:
    raise RuntimeError(f"Suspiciously small source tree: {len(files)}")
if not any(p.name=="gui46.py" for p in files):
    raise RuntimeError("Missing Qt source module")
readme="""DS COMPARE R11.29 - PELNE ZRODLA PRZED KOMPILACJA
================================================
To jest kompletna migawka zrodel programu po zastosowaniu poprawek R11.29,
a przed uruchomieniem PyInstaller. Nie zawiera gotowego EXE.

ZAWARTOSC
- DSCompareV3.py              punkt startowy programu
- dsac29/                     caly silnik, eksport STEP, raporty i UI
- assets/                     ikony i grafiki programu
- tests/                      testy dostarczone ze zrodlami
- requirements.txt            zaleznosci projektu
- BUDUJ_WINDOWS.ps1            instalacja zaleznosci i kompilacja
- MANIFEST_SHA256.txt          kontrola integralnosci plikow

KOMPILACJA LOKALNA (Windows 64-bit):
1. Zainstaluj Python 3.11 x64.
2. Rozpakuj archiwum do katalogu bez polskich znakow w sciezce, np. C:\\DSCompareR1129.
3. Otworz PowerShell w rozpakowanym katalogu.
4. Uruchom:
     powershell -ExecutionPolicy Bypass -File .\\BUDUJ_WINDOWS.ps1
5. Gotowy plik powinien znalezc sie pod: dist\\DSCompare.exe

Uruchomienie zrodel (po zainstalowaniu pakietow):
     python DSCompareV3.py

Zrodla sa zgodne z wersja R11.29 budowana w GitHub Actions.
Wymagane sa Windows x64 i biblioteki OCP oraz Qt.
Kompilacja PyInstaller moze wymagac dostepu do internetu do instalacji pakietow.

Uwaga: Pliki STEP z modeli firmowych NIE sa elementem tej paczki.
"""
build=r"""param([switch]$NoInstall)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.\DSCompareV3.py')) { throw 'Brak DSCompareV3.py' }
if (-not $NoInstall) {
  python -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw 'Pip upgrade failed' }
  python -m pip install -r requirements.txt 'PySide6>=6.8,<6.10' 'vtk>=9.6,<9.7' 'cadquery-ocp==7.9.3.1.1' 'cadquery-ocp-proxy==7.9.3.1.1' 'pyinstaller>=6.11,<7'
  if ($LASTEXITCODE -ne 0) { throw 'Dependencies failed' }
  python -m pip check
  if ($LASTEXITCODE -ne 0) { throw 'Inconsistent dependencies' }
}
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DSCompare --icon assets/DSCompare.ico --collect-all OCP --hidden-import dsac29.parallel_import --hidden-import dsac29.icons_r119 --hidden-import dsac29.z3_support --hidden-import dsac29.import_cache --hidden-import dsac29.gui_modern --hidden-import dsac29.zw3d_launcher --hidden-import dsac29.mass_batch --hidden-import dsac29.mass_drop --hidden-import dsac29.step_diagnostics --hidden-import dsac29.local_tests --add-data "build_info.json;." --add-data "assets/DSCompare.ico;assets" --add-data "assets/DSCompare.png;assets" --distpath "dist" DSCompareV3.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
if (-not (Test-Path '.\dist\DSCompare.exe')) { throw 'No EXE created' }
Write-Host "Gotowe: $PSScriptRoot\dist\DSCompare.exe"
"""
with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
    digests=[]
    for p in files:
        rel=p.relative_to(root).as_posix()
        blob=p.read_bytes()
        digests.append(f"{hashlib.sha256(blob).hexdigest()}  {rel}")
        z.writestr(prefix+rel,blob)
    z.writestr(prefix+"README_ZRODLA.txt",readme)
    z.writestr(prefix+"BUDUJ_WINDOWS.ps1",build)
    z.writestr(prefix+"MANIFEST_SHA256.txt","\n".join(digests)+"\n")
    z.writestr(prefix+"GITHUB_COMMIT.txt",os.environ.get("GITHUB_SHA","")+"\n")
with zipfile.ZipFile(dest) as z:
    bad=z.testzip()
    if bad:raise RuntimeError(f"Bad zip entry: {bad}")
    names=set(z.namelist())
    for name in expected:
        assert prefix+name in names,name
    assert not any(n.endswith(".exe") for n in names)
print(f"R11.29 complete pre-PyInstaller source ZIP: {dest.name}, {len(files)} source files, {dest.stat().st_size} bytes, SHA256={hashlib.sha256(dest.read_bytes()).hexdigest()}",flush=True)
