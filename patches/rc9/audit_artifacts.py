"""Audit actual generated STEP, 3D HTML, report and revision BOM files."""
import csv,json,sys
from pathlib import Path
root=Path(sys.argv[1]);case=sys.argv[2];out=root/'comparison'
summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
result=json.loads((root/'TEST_RESULT.json').read_text(encoding='utf-8'))
assert result.get('status')=='PASS' or result.get('result')=='PASS',result.get('error')
counts=summary['statuses']
assert sum(counts.values())>=max(summary['solids_A'],summary['solids_B'])
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
print(json.dumps({'audit':'PASS','case':case,'counts':counts,
    'step_bytes':step.stat().st_size,'html_bytes':html.stat().st_size,
    'report_bytes':report.stat().st_size,'bom_verified':case=='revision'},ensure_ascii=False))
