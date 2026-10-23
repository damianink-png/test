"""Test DS Compare on actual public CAD assemblies and a translated copy.

NIST / CAx-IF AS1-PE-203: US government test data.
SO-ARM100 Follower: TheRobotStudio (Apache-2.0).
Source assemblies are downloaded by the Windows workflow; no synthetic solids are
substituted for the source geometry.
"""
import json,sys,time,shutil
from pathlib import Path
from OCP.gp import gp_Trsf,gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from dsac29.step_io import load_step,ColoredDocument
from dsac29.cli import process


def test_actual_assembly(input_path, output_dir):
    input_path=Path(input_path).resolve()
    output_dir=Path(output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    source=load_step(str(input_path),max_solids=20000,progress=None)
    n=len(source)
    assert n>=3,f"Source is not a multi-solid assembly: {input_path}: {n}"
    print(f"REAL CAD SOURCE {input_path.name}: {n} solids; {input_path.stat().st_size} bytes",flush=True)
    # Create an actual independent STEP copy translated as an entire assembly.
    translation=(1275.,-395.,210.)
    transform=gp_Trsf()
    transform.SetTranslation(gp_Vec(*translation))
    moved=output_dir/'REAL_ASSEMBLY_MOVED.step'
    writer=ColoredDocument(group_by_status=False,reuse_definitions=True)
    for part in source:
        shifted=BRepBuilderAPI_Transform(part.shape,transform,True).Shape()
        writer.add(shifted,part.name,(.33,.57,.86),1.0)
    details=writer.write(str(moved))
    assert moved.stat().st_size>1000
    check=load_step(str(moved),max_solids=20000,progress=None)
    assert len(check)==n,(n,len(check))
    # Must not silently accept a global displacement as per-part movements.
    decisions=[]
    def decide(proposal):
        decisions.append(proposal)
        if proposal.get('status')=='registered':
            return 'align'
        if proposal.get('status')=='unrelated':
            return 'original'
        return 'original'
    result=output_dir/'DSCOMPARE_RESULT'
    result.mkdir(exist_ok=True)
    _dir,records,error=process(str(input_path),str(moved),str(result),
        step=True,diff_step=False,preview3d=True,revision_style=True,
        auto_align=True,alignment_approval=decide,full_bom=False,
        max_solids=20000,progress=lambda msg:print("TEST:",msg,flush=True))
    assert not error,error
    summary=json.loads((result/'PODSUMOWANIE.json').read_text(encoding='utf8'))
    statuses=summary['statuses']
    unchanged=statuses.get('SAME',0)+statuses.get('RENAMED',0)
    alignment=summary['alignment']
    print('REAL SHIFT RESULT:',input_path.name, 'expected',n, 'unchanged',unchanged, 'alignment', alignment, 'statuses', statuses,flush=True)
    assert unchanged==n,(n,unchanged,statuses,alignment)
    assert not any(statuses.get(k,0) for k in ('REMOVED','ADDED','CHANGED','MOVED'))
    assert alignment.get('applied') is True,alignment
    actual=alignment.get('translation_B_to_A_mm',[])
    assert len(actual)==3 and all(abs(float(actual[k])+translation[k])<.05 for k in range(3)), actual
    scene=(result/'PODGLAD_KOLOROW_3D.html').read_text(encoding='utf8')
    assert 'const scene=[' in scene and 'path_A' in scene and 'path_B' in scene
    assert 'Rewizja B' in scene and 'function pathSegments' in scene
    assert summary['preview_3d']['pominiete']==0
    assert summary['preview_3d']['elementy']==n
    assert (result/'POROWNANIE_KOLORY.step').stat().st_size>1000
    assert summary['main_step_ready']
    outcome={'source_file':input_path.name,'source_parts':n,
             'translated_mm':translation,'aligned_B_to_A':actual,
             'unchanged':unchanged,'statuses':statuses,
             'seconds':round(time.monotonic()-start,2),
             'source_url':{
              'as1_pe_203.stp':'https://github.com/kovacsv/occt-import-js/blob/main/test/testfiles/cax-if/as1_pe_203.stp',
              'SO_5DOF_ARM100_Assembly.step':'https://github.com/TheRobotStudio/SO-ARM100/blob/main/STEP/SO100/Follower_Specific/SO_5DOF_ARM100_Assembly.step'
             }.get(input_path.name,''),
             'html_file':str((result/'PODGLAD_KOLOROW_3D.html').name)}
    (output_dir/'WYNIK_TESTU_RZECZYWISTEGO_ZLOZENIA.json').write_text(json.dumps(outcome,indent=2,ensure_ascii=False),encoding='utf8')
    # A standalone copy of the real preview at the artifact root.
    shutil.copyfile(result/'PODGLAD_KOLOROW_3D.html',output_dir/'RZECZYWISTE_ZLOZENIE_PODGLAD_3D.html')
    print('REAL CAD ASSEMBLY TEST PASS',outcome,flush=True)
    return outcome


if __name__=='__main__':
    test_actual_assembly(sys.argv[1],sys.argv[2])
