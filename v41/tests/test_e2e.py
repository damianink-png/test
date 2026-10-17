from pathlib import Path
import sys
from dsac29.cli import process
from dsac29.step_io import load_step


def test_sample_step_end_to_end(tmp_path):
    import generuj_przykladowe_step as gen
    gen.main()
    folder=Path(gen.__file__).parent/'samples'
    a=load_step(str(folder/'MODEL_A.step'))
    b=load_step(str(folder/'MODEL_B.step'))
    assert len(a)==len(b)==4
    result, rec,err=process(str(folder/'MODEL_A.step'),str(folder/'MODEL_B.step'),tmp_path,progress=None)
    assert err is None
    statuses=[r.status for r in rec]
    assert sorted(statuses)==sorted(['CHANGED','RENAMED','MOVED','REMOVED','ADDED']), statuses
    again=load_step(str(tmp_path/'POROWNANIE_KOLORY.step'))
    assert len(again)==5  # 4 current solids B plus one genuinely removed A
    assert (tmp_path/'RAPORT.html').exists()
    assert (tmp_path/'BOM_A.csv').exists()
