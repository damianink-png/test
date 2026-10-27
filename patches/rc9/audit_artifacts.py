"""Audit actual generated STEP, 3D HTML, report and revision BOM files."""
import csv,hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);case=sys.argv[2];out=root/'comparison'
summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
result=json.loads((root/'TEST_RESULT.json').read_text(encoding='utf-8'))
assert result.get('status')=='PASS' or result.get('result')=='PASS',result.get('error')
counts=summary['statuses']
# Each matched occurrence belongs to both revisions; ADDED belongs only
# to B, REMOVED only to A. A weak >= bound cannot detect dropped/duplicated
# occurrences and could falsely pass an incomplete STEP/HTML/BOM audit.
known={'SAME','MOVED','CHANGED','ADDED','REMOVED'}
unexpected=set(counts)-known
assert not unexpected,f'Unexpected status categories: {sorted(unexpected)}'
assert all(isinstance(v,int) and v>=0 for v in counts.values()),'Invalid status count'
matched=sum(counts.get(key,0) for key in ('SAME','MOVED','CHANGED'))
assert matched+counts.get('REMOVED',0)==summary['solids_A'],(
    'Revision A occurrence accounting mismatch')
assert matched+counts.get('ADDED',0)==summary['solids_B'],(
    'Revision B occurrence accounting mismatch')
assert summary.get('tolerance_mm',.01)==.01
step=out/'POROWNANIE_KOLORY.step'
assert step.is_file() and step.stat().st_size>1000,'Actual colored STEP absent'
with step.open('rb') as f:head=f.read(1024)
assert b'ISO-10303-21' in head,'STEP header invalid'
html=out/'PODGLAD_KOLOROW_3D.html'
assert html.is_file() and html.stat().st_size>1000,'Actual 3D HTML absent'
text=html.read_text(encoding='utf-8')
assert 'const scene=' in text and 'mesh_id' in text,'HTML 3D scene missing'
report=out/'RAPORT.html'
assert report.is_file() and report.stat().st_size>1000,'Actual HTML report absent'
report_text=report.read_text(encoding='utf-8')
assert 'data-status=' in report_text
assert report_text.count('data-status=')>=sum(counts.values()),'Report rows missing'
if case=='revision':
    for role in ('A','B'):
        groups=out/f'BOM_GRUPY_{role}.json'
        assert groups.is_file(),f'Missing BOM {role} groups'
        entries=json.loads(groups.read_text(encoding='utf-8'))
        expected=summary[f'solids_{role}']
        assert sum(x['ilosc'] for x in entries)==expected,f'BOM {role} count mismatch'
        occurrences=[item['index'] for group in entries for item in group['wystapienia']]
        assert sorted(occurrences)==list(range(expected)),f'BOM {role} missing/duplicate occurrence'
        csv_file=out/f'BOM_{role}.csv'
        assert csv_file.is_file(),'BOM CSV missing'
        with csv_file.open(encoding='utf-8-sig',newline='') as handle:
            rows=list(csv.reader(handle,delimiter=';'))
        assert sum(int(row[1]) for row in rows[1:])==expected
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()
print(json.dumps({'audit':'PASS','case':case,'counts':counts,
    'step_bytes':step.stat().st_size,'html_bytes':html.stat().st_size,
    'report_bytes':report.stat().st_size,
    'step_sha256':sha256(step),'html_sha256':sha256(html),
    'report_sha256':sha256(report),
    'bom_verified':case=='revision'},ensure_ascii=False))
