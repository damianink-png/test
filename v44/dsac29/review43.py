"""Manual adjudication sidecar. NEVER changes the original automatic B-Rep report.

A user confirmation identifies matching engineering parts, NOT proof that their
B-Rep geometries are equal. Original geometry statuses remain visible.
"""
from __future__ import annotations
import csv,hashlib,json,os,tempfile
from pathlib import Path
from datetime import datetime,timezone

SIDEFILE='WERYFIKACJA_RECZNA.json'
CSVFILE='ZMIANY_WERYFIKACJA.csv'

class ReviewError(ValueError): pass


def _base(folder):
    path=Path(folder)/'PODSUMOWANIE.json'
    raw=path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')),hashlib.sha256(raw).hexdigest()


def _candidate(base,a,b):
    records=base['records']
    if type(a) is not int or type(b) is not int or a<0 or b<0:
        raise ReviewError('Indeksy muszą być nieujemnymi liczbami całkowitymi')
    ra=[(i,r) for i,r in enumerate(records) if r.get('a_index')==a]
    rb=[(i,r) for i,r in enumerate(records) if r.get('b_index')==b]
    if len(ra)!=1 or len(rb)!=1:raise ReviewError('Nie ma jednoznacznych wystąpień A i B')
    ia,ar=ra[0];ib,br=rb[0]
    if ia==ib and ar.get('status')=='UNCERTAIN':return 'uncertain',[ia]
    if ia!=ib and ar.get('b_index') is None and br.get('a_index') is None and ar.get('status')=='REMOVED' and br.get('status')=='ADDED':
        return 'manual_pair',[ia,ib]
    raise ReviewError('Wybierz niepewną parę albo usuniętą bryłę A i dodaną bryłę B')


def load(folder):
    base,digest=_base(folder)
    path=Path(folder)/SIDEFILE
    if not path.exists():return {'schema':1,'base_sha256':digest,'decisions':[]}
    doc=json.loads(path.read_text(encoding='utf-8'))
    if doc.get('schema')!=1 or doc.get('base_sha256')!=digest:
        raise ReviewError('Raport bazowy został zmieniony. Zachowano stare decyzje, ale nie wolno ich zastosować do innej analizy.')
    decisions=doc.get('decisions')
    if not isinstance(decisions,list):raise ReviewError('Niepoprawny format decyzji')
    occupied_a=set();occupied_b=set()
    for d in decisions:
        kind,source=_candidate(base,d['a_index'],d['b_index'])
        if d.get('kind')!=kind or d['a_index'] in occupied_a or d['b_index'] in occupied_b:
            raise ReviewError('Duplikat lub niepoprawna ręczna para')
        occupied_a.add(d['a_index']);occupied_b.add(d['b_index'])
    return doc


def _atomic_write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def save(folder,doc):
    # Validate the base checksum and all decisions before committing.
    base,digest=_base(folder)
    if doc.get('base_sha256')!=digest:raise ReviewError('Nieaktualny wynik analizy')
    seen_a=set();seen_b=set()
    for d in doc['decisions']:
        kind,_=_candidate(base,d['a_index'],d['b_index'])
        if kind!=d['kind'] or d['a_index'] in seen_a or d['b_index'] in seen_b:raise ReviewError('Konflikt przyporządkowania')
        seen_a.add(d['a_index']);seen_b.add(d['b_index'])
    folder=Path(folder)
    # Supplemental CSV is derived ONLY from source CSV; original remains untouched.
    source=folder/'ZMIANY.csv'
    with source.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter=';');headers=list(reader.fieldnames or [])
        rows=list(reader)
    if len(rows)!=len(base['records']):raise ReviewError('Liczba rekordów CSV różni się od PODSUMOWANIE.json')
    for row in rows:row.update({'Decyzja użytkownika':'','Ręczna para A/B':'','Notatka weryfikacji':''})
    for d in doc['decisions']:
        _,ids=_candidate(base,d['a_index'],d['b_index'])
        tag=f"A#{d['a_index']} ↔ B#{d['b_index']}"
        for i in ids:
            rows[i]['Decyzja użytkownika']='Potwierdzono powiązanie ręcznie — bez potwierdzenia równości B-Rep'
            rows[i]['Ręczna para A/B']=tag
            rows[i]['Notatka weryfikacji']=d.get('note','')
    import io
    buf=io.StringIO(newline='');out=csv.DictWriter(buf,fieldnames=headers+['Decyzja użytkownika','Ręczna para A/B','Notatka weryfikacji'],delimiter=';')
    out.writeheader();out.writerows(rows)
    _atomic_write(folder/CSVFILE,'\ufeff'+buf.getvalue())
    _atomic_write(folder/SIDEFILE,json.dumps(doc,ensure_ascii=False,indent=2))
    return doc


def confirm(folder,a,b,note=''):
    doc=load(folder);base,_=_base(folder)
    kind,_=_candidate(base,a,b)
    if len(note)>2000:raise ReviewError('Notatka jest za długa')
    for d in doc['decisions']:
        if d['a_index']==a and d['b_index']==b:raise ReviewError('Ta para jest już zweryfikowana')
        if d['a_index']==a or d['b_index']==b:raise ReviewError('Ten element ma już przypisaną inną parę')
    doc['decisions'].append({'kind':kind,'a_index':a,'b_index':b,'note':note,
                             'checked_at':datetime.now(timezone.utc).isoformat()})
    return save(folder,doc)


def revoke(folder,a,b):
    doc=load(folder)
    old=len(doc['decisions'])
    doc['decisions']=[d for d in doc['decisions'] if not (d['a_index']==a and d['b_index']==b)]
    if len(doc['decisions'])==old:raise ReviewError('Nie znaleziono zatwierdzenia tej pary')
    return save(folder,doc)


def for_record(base,decision):
    # O(1) lookup in GUI after a single preprocessing pass, if needed.
    return [i for i,r in enumerate(base['records']) if r.get('a_index')==decision['a_index'] or r.get('b_index')==decision['b_index']]
