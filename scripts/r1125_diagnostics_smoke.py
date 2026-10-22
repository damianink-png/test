"""R11.25 end-to-end synthetic diagnostics and sanitized TXT check."""
from pathlib import Path
from tempfile import TemporaryDirectory
from dsac29.local_tests import run,update_zw3d_results,NAME,STEPS
from dsac29.worker_v37 import main

with TemporaryDirectory() as tmp:
    folder=Path(tmp)/'SELF_TEST'
    # Exercise actual GUI's worker backend dispatch, progress markers and TXT.
    code=main(['--worker','diagnostic','--output',str(folder)])
    text=(folder/NAME).read_text('utf8')
    assert code==0,text
    import json
    payload=json.loads((folder/'_WYNIK_V37.json').read_text('utf8'))
    assert payload['ok'] and payload['passed']==payload['total'],payload
    assert payload['total']>=7,payload
    assert 'WYNIK:' in text and 'FAIL |' not in text
    for key,name in STEPS:assert (folder/name).is_file(),name
    assert 'C:\\' not in text and 'D:\\' not in text and str(folder) not in text, 'privacy: exposed local folder'
    assert 'T_REMOVED' not in text and 'T_ADDED' not in text,'privacy: exposed geometry/product names'
    obs={
        'STANDARDOWY':{'absr':11,'groups':'Tak'},
        'BEZ_KORZENIA':{'absr':8,'groups':'Tak'},
        'PLASKI':{'absr':0,'groups':'Nie'},
    }
    update_zw3d_results(folder/NAME,obs)
    updated=(folder/NAME).read_text('utf8')
    for label,value in [('Standardowy','11'),('Bez korzenia','8'),('Plaski','0')]:
        assert f'{label}: ABSR={value}' in updated,updated
    assert 'wyniki' not in str(payload.get('error','')).lower()
print('R11.25 PASS: real worker synthetic STEP/BRep/mass structure tests, complete private TXT and manual ZW3D numbers')
