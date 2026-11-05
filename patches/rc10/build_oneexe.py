"""Build the patched RC10 with the original PyInstaller options as one EXE."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
build = (root / 'BUDUJ_WINDOWS.ps1').read_text(encoding='utf-8-sig')
lines = [line for line in build.splitlines() if line.startswith('python -m PyInstaller ')]
if len(lines) != 1 or '--onedir' not in lines[0]:
    raise SystemExit('Unexpected RC10 build command')
args = shlex.split(lines[0])[1:]
args[args.index('--onedir')] = '--onefile'
args.extend(['--hidden-import', 'dsac29.repetition'])
info_path = root / 'build_info.json'
info = json.loads(info_path.read_text(encoding='utf-8-sig'))
info.update(revision='RC10 Common + przesunięcie 2026-11-05',
            packaging='OneEXE', source_commit=os.environ.get('GITHUB_SHA', 'local'))
info_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding='utf-8')
subprocess.run([sys.executable, *args], cwd=root, check=True)
exe = root / 'dist' / 'DSCompare.exe'
if not exe.is_file():
    raise SystemExit('OneEXE missing')
print(f'OneEXE ready: {exe} ({exe.stat().st_size} bytes)')
