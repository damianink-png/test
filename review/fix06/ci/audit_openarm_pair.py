"""Strict truth audit for OpenArm v1.0/v1.1; not a partial-report smoke test.

Find the actual comparison summary, report every uncertain pairing and
group the geometry failures. A normal partial report is a strict-test FAIL.
"""
from collections import Counter
from pathlib import Path
import json
import sys

root=Path(sys.argv[1])
matches=sorted(root.rglob('PODSUMOWANIE.json'),key=lambda p:len(p.parts))
if not matches:
    print('OPENARM_STRICT_FAIL: no PODSUMOWANIE.json under',root,flush=True)
    raise SystemExit(2)
path=matches[0]
data=json.loads(path.read_text(encoding='utf-8-sig'))
records=data.get('records') or []
statuses=Counter(r.get('status','MISSING') for r in records)
overlap=data.get('revision_overlap') or {}
failed=overlap.get('failed_pairs') or []
classes=Counter()
for entry in failed:
    error=str(entry.get('error',''))
    if 'limit czasu' in error or 'limit liczby' in error or 'Nie wykonano testu' in error:
        classes['LIMIT']+=1
    elif 'Common' in error or 'common' in error:
        classes['COMMON']+=1
    elif 'Cut' in error or 'podział' in error or 'regions' in error:
        classes['CUT_OR_REGIONS']+=1
    else:
        classes['OTHER']+=1
uncertain=[r for r in records if r.get('status')=='UNCERTAIN']
report={
    'summary':str(path),
    'source_A':data.get('source_A'),
    'source_B':data.get('source_B'),
    'solids_A':data.get('solids_A'),
    'solids_B':data.get('solids_B'),
    'analysis_complete':data.get('analysis_complete'),
    'material_analysis_complete':data.get('material_analysis_complete'),
    'statuses':dict(statuses),
    'revision_overlap':{k:v for k,v in overlap.items() if k not in ('failed_pairs','exclusion_witnesses')},
    'failure_classes':dict(classes),
    'failed_pairs_count':overlap.get('failed_pairs_total',len(failed)),
    'first_failed_pairs':failed[:25],
    'uncertain_examples':[
        {k:r.get(k) for k in ('a_index','b_index','name_a','name_b','note','diagnostic_reason','blocked_operation_operand')}
        for r in uncertain[:20]
    ],
    'strict_pass':bool(data.get('analysis_complete') is True
                       and data.get('material_analysis_complete') is not False
                       and len(uncertain)==0),
}
dest=root/'openarm-strict-diagnostic.json'
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print('OPENARM_PAIR_AUDIT_BEGIN',flush=True)
print(json.dumps(report,ensure_ascii=False,indent=2,default=str)[:20000],flush=True)
print('OPENARM_PAIR_AUDIT_END',flush=True)
if not report['strict_pass']:
    print('OPENARM_STRICT_FAIL: at least one unverified component or incomplete geometry',flush=True)
    raise SystemExit(1)
print('OPENARM_STRICT_PASS: both assemblies fully compared',flush=True)
