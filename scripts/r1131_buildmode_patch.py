"""R11.31: package stable onedir Windows application to avoid PyInstaller _MEI cleanup.

No onefile nested extraction for GUI or workers: launch from DSCompare folder.
"""
from pathlib import Path
import os
root=Path(os.environ['GITHUB_WORKSPACE'])
# Update the precompile source's build helper for stable onedir output.
package_script=root/'scripts/r1130_package_complete_sources.py'
if not package_script.is_file():raise RuntimeError('Source packaging helper not found')
s=package_script.read_text('utf8')
if s.count(' --onefile --windowed')!=1:
    raise RuntimeError('Expected single original PyInstaller build command in readme')
s=s.replace(' --onefile --windowed',' --onedir --windowed')
s=s.replace(r'dist\\DSCompare.exe',r'dist\\DSCompare\\DSCompare.exe')
s=s.replace('Gotowe: $PSScriptRoot\\dist\\DSCompare.exe',
            'Gotowe: $PSScriptRoot\\dist\\DSCompare\\DSCompare.exe')
package_script.write_text(s,encoding='utf8')
print('Updated source build helper to onedir; frozen Windows UI/worker can no longer create _MEI temp extractions')
