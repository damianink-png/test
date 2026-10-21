"""R11.24: STEP ABSR diagnostics + optional side-by-side flat variant, no animation changes."""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
def change(path,old,new):
 p=root/path
 s=p.read_text('utf8')
 n=s.count(old)
 if n!=1:raise RuntimeError(f'{path}: expected 1 anchor ({old[:96]!r}), got {n}')
 p.write_text(s.replace(old,new,1),encoding='utf8')

change('dsac29/worker_v37.py',
 "    p.add_argument('--flat-zw3d',action='store_true',help='Write solid-only flat STEP without ABSR assembly nodes')",
 "    p.add_argument('--flat-zw3d',action='store_true',help='Write solid-only flat STEP without ABSR assembly nodes')\n"
 "    p.add_argument('--absr-test',action='store_true',help='Add independent flat STEP for importer testing; native STEP remains unchanged')")
change('dsac29/worker_v37.py',
 "            os.environ['DSCOMPARE_FLAT_FALLBACK']='1' if ns.flat_zw3d else '0'",
 "            os.environ['DSCOMPARE_FLAT_FALLBACK']='1' if ns.flat_zw3d else '0'\n"
 "            os.environ['DSCOMPARE_ABSR_TEST_OUTPUT']='1' if ns.absr_test else '0'")
change('dsac29/gui45.py',
 "            if getattr(self,'zw3d_flat_output',None) is not None and self.zw3d_flat_output.isChecked():args+=['--flat-zw3d']",
 "            if getattr(self,'zw3d_flat_output',None) is not None and self.zw3d_flat_output.isChecked():args+=['--flat-zw3d']\n"
 "            if getattr(self,'absr_test_output',None) is not None and self.absr_test_output.isChecked():args+=['--absr-test']")
change('dsac29/gui_modern.py',
 "  rp.addRow(self.zw3d_flat_output)\n  warning=QLabel('Hierarchia podzłożeń wymaga kontenerów STEP. Nie można ich bezpiecznie usuwać z pliku po eksporcie.')",
 """  rp.addRow(self.zw3d_flat_output)
  self.absr_test_output=QCheckBox('Test ABSR: generuj drugi STEP bez kontenerów')
  self.absr_test_output.setChecked(False)
  self.absr_test_output.setToolTip('Zapisuje dwa osobne pliki do testu w ZW3D: zwykły STEP z podzłożeniami oraz TEST_ABSR/STEP_BEZ_ABSR.step. Drugi jest płaski. Wymaga dodatkowego czasu eksportu.')
  rp.addRow(self.absr_test_output)
  warning=QLabel('Hierarchia podzłożeń wymaga kontenerów STEP. Nie można ich bezpiecznie usuwać z pliku po eksporcie.')""")

p=root/'dsac29/step_io.py'
s=p.read_text('utf8')
anchor="""    result=_export_revision_step(path,list(records),a_parts,b_parts,colors,old_alpha,progress,
                                 reuse_definitions=False,flat_zw3d=flat)
    result['tryb_zapisu']='plaski_awaryjny' if flat else 'podzlozenia_bez_pustych_lisci'
    return result"""
assert s.count(anchor)==1
new="""    import time
    from .step_diagnostics import save as save_step_diagnostics
    started=time.perf_counter()
    rows=list(records)
    result=_export_revision_step(path,rows,a_parts,b_parts,colors,old_alpha,progress,
                                 reuse_definitions=False,flat_zw3d=flat)
    result['tryb_zapisu']='plaski_awaryjny' if flat else 'podzlozenia_bez_pustych_lisci'
    result['czas_zapisu_i_weryfikacji_s']=round(time.perf_counter()-started,3)
    try:
        diagnostic=save_step_diagnostics(path,result)
        result['raport_diagnostyki_step']=str(Path(diagnostic).name)
    except Exception as err:
        # A valid verified STEP must remain available even if extra JSON fails.
        result['blad_dodatkowej_diagnostyki_step']=str(err)
        if progress:progress('OSTRZEŻENIE: dodatkowy raport STEP: '+str(err))
    if os.environ.get('DSCOMPARE_ABSR_TEST_OUTPUT')=='1' and not flat:
        folder=Path(path).parent/'TEST_ABSR'
        try:
            folder.mkdir(exist_ok=True)
            candidate=folder/'STEP_BEZ_ABSR.step'
            if progress:progress('Test ABSR: zapis dodatkowego płaskiego STEP (bez podzłożeń)...')
            second=_export_revision_step(str(candidate),rows,a_parts,b_parts,colors,old_alpha,progress,
                                         reuse_definitions=False,flat_zw3d=True)
            report=save_step_diagnostics(candidate,second)
            result['test_absr_step']=str(candidate.relative_to(Path(path).parent))
            result['test_absr_raport']=str(Path(report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: drugi plik STEP jest gotowy w folderze TEST_ABSR.')
        except Exception as err:
            # The primary native assembly STEP is already committed.
            result['test_absr_blad']=str(err)
            (folder/'BLAD_TESTU_ABSR.txt').write_text(str(err),encoding='utf8')
            if progress:progress('OSTRZEŻENIE: testowy STEP bez ABSR nie powiódł się: '+str(err))
    return result"""
p.write_text(s.replace(anchor,new,1),encoding='utf8')
(root/'VERSION.txt').write_text('R11.24\\n',encoding='utf8')
info=root/'build_info.json'
if info.is_file():
 d=json.loads(info.read_text('utf8'))
 d['version']='R11.24 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 d['absr']='Native STEP unchanged; experimental flat sidecar & diagnostic if requested'
 info.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('R11.24 STEP side-by-side diagnostics patch installed')
