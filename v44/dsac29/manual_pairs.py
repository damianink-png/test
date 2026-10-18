"""Explicit user identity decisions, independently checked for geometry."""
import hashlib
import numpy as np
from .compare import Record
from .geometry import equivalent_world,equivalent_rigid
from .names import genuine_rename

def fingerprint(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def apply_pairs(a,b,records,pairs,tolerance):
    aa=[p[0] for p in pairs];bb=[p[1] for p in pairs]
    if len(set(aa))!=len(aa) or len(set(bb))!=len(bb):raise ValueError('Część może należeć tylko do jednej pary ręcznej')
    if any(type(i)!=int or i<0 or i>=len(a) for i in aa) or any(type(j)!=int or j<0 or j>=len(b) for j in bb):raise ValueError('Nieprawidłowe indeksy par')
    touched_a=set(aa);touched_b=set(bb);keep=[];orphan_a=set();orphan_b=set()
    for r in records:
        if r.a_index in touched_a or r.b_index in touched_b:
            if r.a_index is not None:orphan_a.add(r.a_index)
            if r.b_index is not None:orphan_b.add(r.b_index)
        else:keep.append(r)
    for i,j in pairs:
        d=b[j].center-a[i].center;angle=None
        try:
            if equivalent_world(a[i],b[j],tolerance):status='RENAMED' if genuine_rename(a[i],b[j]) else 'SAME'
            else:
                same,rotation,_=equivalent_rigid(a[i],b[j],tolerance)
                status='MOVED' if same else 'CHANGED'
                if same and rotation is not None:angle=float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2,-1,1))))
            note='Tożsamość pary wskazana przez użytkownika; geometria sprawdzona B-Rep'
        except Exception as exc:status='UNCERTAIN';note='Para użytkownika; błąd sprawdzenia geometrii: '+str(exc)
        keep.append(Record(i,j,status,note,float(np.linalg.norm(d)),*map(float,d),float(b[j].volume-a[i].volume),angle,'Para użytkownika'))
    for i in sorted(orphan_a-touched_a):keep.append(Record(i,None,'UNCERTAIN','Pozostała część A po ręcznej korekcie pary'))
    for j in sorted(orphan_b-touched_b):keep.append(Record(None,j,'UNCERTAIN','Pozostała część B po ręcznej korekcie pary'))
    keep.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
    assert sorted(r.a_index for r in keep if r.a_index is not None)==list(range(len(a)))
    assert sorted(r.b_index for r in keep if r.b_index is not None)==list(range(len(b)))
    return keep
