"""Runs the frozen program, not source modules, on the Windows build host."""
import json,os,subprocess,sys,struct
from pathlib import Path
out=Path(sys.argv[1]).resolve();exe=out/'DSCompareV3.exe'
checks=out/'WERYFIKACJA';checks.mkdir(exist_ok=True)
env=dict(os.environ,QT_QPA_PLATFORM='offscreen')
def run(args):
    p=subprocess.run([str(exe),*map(str,args)],env=env,timeout=180)
    assert p.returncode==0,(args,p.returncode)
run(['--worker','compare','--a',out/'samples/MODEL_A.step','--b',out/'samples/MODEL_B.step',
     '--output',checks/'WYNIK_TESTOWY','--generate-step','--diff-step','--schema','AP214IS'])
diag=json.loads((checks/'WYNIK_TESTOWY/DIAGNOSTYKA_KOLOROW.json').read_text(encoding='utf-8'))
assert diag['pokolorowane_powierzchnie']>0 and diag['powierzchnie_bez_koloru']==0
result=json.loads((checks/'WYNIK_TESTOWY/_WYNIK_V37.json').read_text(encoding='utf-8'))
assert result['ok'] and result['blad_step'] is None
run(['--worker','mesh','--input',checks/'WYNIK_TESTOWY/POROWNANIE_KOLORY.step','--output',checks/'MESH'])
assert (checks/'MESH/SCENA_3D.npz').exists()
run(['--smoke-test-ui',checks/'GUI'])
assert (checks/'GUI/UI_OK.json').exists()
# Load DLL outside CAD solely to verify x64 load/dependencies/exports, not Init.
import ctypes
bridge=ctypes.WinDLL(str(out/'DSAssemblyCompare2019.dll'))
for symbol in ('DSAssemblyCompare2019Init','DSAssemblyCompare2019Exit'):
    assert getattr(bridge,symbol)
(checks/'TESTY_GOTOWEGO_PROGRAMU.json').write_text(json.dumps({
 'version':'4.1','packaged_compare':'PASS','face_color_roundtrip':'PASS',
 'packaged_mesh':'PASS','packaged_gui':'PASS','dll_load_and_exports':'PASS',
 'ZW3D_runtime':'NOT_TESTED'},indent=2),encoding='utf-8')
print('Frozen EXE, STEP colors, mesh, GUI and DLL load: PASS')
