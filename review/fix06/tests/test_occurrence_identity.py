"""Full-geometry STEP repetition tests independent of AP203/AP214 metadata.

Regression reproduces 150 occurrences emitted as reference placements in
one export and 150 independent, globally baked solids in another. A geometry
change or unmatched copy can never inherit a family proof.
"""
from collections import Counter
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt,gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.geometry_registry import GeometryRegistry
from dsac29.occurrence_identity import prepare_occurrence_identities
from dsac29 import compare as comparator


def make_repeated(n=150,changed=-1,extra=0):
    master=BRepPrimAPI_MakeBox(7.,11.,13.).Shape()
    old=[];new=[]
    for i in range(n):
        x,y,z=float(i*23),float((i%7)*31),float((i%5)*19)
        t=gp_Trsf();t.SetTranslation(gp_Vec(x,y,z))
        old.append(describe(master.Moved(TopLoc_Location(t)),'PROFILE','A/'+str(i)))
        length=13.5 if i==changed else 13.
        shape=BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),7.,11.,length).Shape()
        new.append(describe(shape,'PROFILE','B/'+str(i)))
    for i in range(extra):
        shape=BRepPrimAPI_MakeBox(gp_Pnt(50000.+i*40,0.,0.),7.,11.,13.).Shape()
        new.append(describe(shape,'EXTRA','B/extra'+str(i)))
    return old,new


def test_150_zw3d_refs_vs_150_baked_independent_solids_are_same(monkeypatch):
    old,new=make_repeated()
    new=new[::2]+new[1::2]
    calls=[]
    def forbid_unneeded(*args,**kwargs):
        calls.append(1)
        raise AssertionError('Exact identical normalized complete B-Rep needs no native Boolean')
    monkeypatch.setattr(comparator,'guarded_world_equivalent',forbid_unneeded)
    monkeypatch.setattr(comparator,'guarded_world_reexport',forbid_unneeded)
    records=comparator.compare(old,new,revision_only=True,exact_serialization=True)
    assert Counter(r.status for r in records)=={'SAME':150}
    assert sorted(r.a_index for r in records)==list(range(150))
    assert sorted(r.b_index for r in records)==list(range(150))
    assert not calls


def test_150_repetitions_one_real_change_must_not_be_green(monkeypatch):
    old,new=make_repeated(changed=13,extra=1)
    # An untrusted numerical descriptor or a matching name must never
    # establish a positive equality for the changed occurrence.
    records=comparator.compare(old,new,revision_only=True,exact_serialization=True)
    same=[r for r in records if r.status in ('SAME','RENAMED')]
    assert len(same)==149
    assert all(r.a_index!=13 for r in same)
    assert all(r.b_index!=13 for r in same)
    assert len({r.a_index for r in records if r.a_index is not None})==150
    assert len({r.b_index for r in records if r.b_index is not None})==151


def test_normalized_brep_is_exact_and_original_world_origin_is_preserved():
    old,new=make_repeated(n=8)
    result=prepare_occurrence_identities(old,new)
    assert result['proven']==16
    hashes={p._dscompare_normalized_digest for p in old+new}
    assert len(hashes)==1
    for i in range(8):
        m_a=comparator._location_matrix(old[i])
        m_b=comparator._location_matrix(new[i])
        assert np.allclose(m_a,m_b,atol=1e-10,rtol=0)
    # The canonical local identity is NOT a world-position identity.
    assert not np.allclose(comparator._location_matrix(old[0]),
                           comparator._location_matrix(old[1]))


def test_geometry_changed_equal_name_cannot_share_normalized_definition():
    old,new=make_repeated(n=8,changed=2)
    prepare_occurrence_identities(old,new)
    assert new[2]._dscompare_normalized_digest!=old[2]._dscompare_normalized_digest


def test_xcaf_reference_identity_is_source_scoped_not_name_scoped():
    a=describe(BRepPrimAPI_MakeBox(7.,11.,13.).Shape(),'same name','A/1')
    b=describe(BRepPrimAPI_MakeBox(7.,11.,13.).Shape(),'different name','A/2')
    c=describe(BRepPrimAPI_MakeBox(7.,11.,13.).Shape(),'same name','B/1')
    a.step_definition_key=('source-A.step','0:1:1:10',1)
    b.step_definition_key=('source-A.step','0:1:1:10',1)
    c.step_definition_key=('source-B.step','0:1:1:10',1)
    registry=GeometryRegistry()
    assert registry.definition(a)==registry.definition(b)
    assert registry.definition(c)!=registry.definition(a)


def test_no_false_same_for_changed_baked_geometry():
    old,new=make_repeated(n=8,changed=3)
    prepare_occurrence_identities(old,new)
    reg=GeometryRegistry()
    assert reg.definition(old[3])!=reg.definition(new[3])
    assert reg.definition(old[0])==reg.definition(new[0])


def test_150_repetitions_plus_one_real_added_solid_is_accounted_once():
    old,new=make_repeated(extra=1)
    records=comparator.compare(old,new,revision_only=True,exact_serialization=True)
    counts=Counter(r.status for r in records)
    assert counts['SAME']==150
    assert counts['ADDED']==1
    assert counts['UNCERTAIN']==0
    assert sorted(r.a_index for r in records if r.a_index is not None)==list(range(150))
    assert sorted(r.b_index for r in records if r.b_index is not None)==list(range(151))


def test_canonical_family_never_claims_translated_assembly_same_without_frame_alignment():
    # Identical geometry in a different location is not SAME in original
    # assembly coordinates. The registration step must prove the global
    # frame before any reused occurrence certificate can be applied.
    old,new=make_repeated(n=8)
    transform=gp_Trsf()
    transform.SetTranslation(gp_Vec(700.,0.,0.))
    new=[describe(p.shape.Moved(TopLoc_Location(transform)),
                  p.name,p.path) for p in new]
    result=comparator.compare(old,new,revision_only=True,exact_serialization=True)
    assert not any(r.status in ('SAME','RENAMED') for r in result)


def test_same_volume_distinct_shape_cannot_be_certified_by_descriptors():
    old,new=make_repeated(n=8)
    new[3]=describe(BRepPrimAPI_MakeBox(gp_Pnt(69.,0.,0.),10.,10.,10.01).Shape(),
                    'PROFILE','B/changed-same-volume')
    prepare_occurrence_identities(old,new)
    context=GeometryRegistry()
    assert context.definition(old[3])!=context.definition(new[3])


def test_xcaf_repeated_references_are_serialized_once_despite_separate_native_wrappers(monkeypatch):
    # In some STEP transfers, IsPartner() is false for wrappers referring
    # to the same document definition. XCAF identity stays authoritative
    # only INSIDE the same source and for the same solid index.
    from dsac29 import occurrence_identity
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    count=[]
    original=occurrence_identity._canonical
    def measure(*args,**kwargs):
        count.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(occurrence_identity,'_canonical',measure)
    a=[]
    for i in range(60):
        shape=BRepPrimAPI_MakeBox(7.,11.,13.).Shape()
        tr=gp_Trsf()
        tr.SetTranslation(gp_Vec(float(20*i),0.,0.))
        part=describe(shape.Moved(TopLoc_Location(tr)),'same','A/'+str(i))
        part.step_definition_key=('source-A.step','0:1:1:45',1)
        a.append(part)
    assert not a[0].shape.IsPartner(a[1].shape)
    stats=prepare_occurrence_identities(a,[])
    assert stats['selected']==60 and stats['proven']==60
    assert len(count)==1, 'Same source XCAF target must serialize once'
    assert stats['xcaf_reuse']==59
    assert len({p._dscompare_normalized_digest for p in a})==1
    assert not np.allclose(comparator._location_matrix(a[0]),
                           comparator._location_matrix(a[1]))


def test_xcaf_source_cache_never_crosses_files_or_different_subsolids(monkeypatch):
    from dsac29 import occurrence_identity
    n=[]
    original=occurrence_identity._canonical
    def count(*args,**kwargs):
        n.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(occurrence_identity,'_canonical',count)
    p=[]
    for j in range(5):
        for filename,number,dx in [('source-A.step',1,0.),('source-B.step',1,100.),
                                   ('source-A.step',2,300.)]:
            shape=BRepPrimAPI_MakeBox(7.+(number-1),11.,13.).Shape()
            tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(dx+20*j),0.,0.))
            a=describe(shape.Moved(TopLoc_Location(tr)),'part','file/'+str(j))
            a.step_definition_key=(filename,'0:1:1:45',number)
            p.append(a)
    stats=prepare_occurrence_identities(p,[])
    assert stats['selected']==15 and stats['proven']==15
    assert len(n)==3
    assert stats['xcaf_reuse']==12
    assert p[0]._dscompare_normalized_digest!=p[2]._dscompare_normalized_digest


def test_large_xcaf_reference_population_uses_definition_budget():
    """Many occurrences of two source-scoped XCAF parts still get full B-Rep."""
    from types import SimpleNamespace

    first=BRepPrimAPI_MakeBox(7.,11.,13.).Shape()
    second=BRepPrimAPI_MakeBox(7.,11.,13.).Shape()
    a=[SimpleNamespace(shape=first,volume=1001.,area=622.,
                       step_definition_key=('first.step','0:1:1:8',1))
       for _ in range(21)]
    b=[SimpleNamespace(shape=second,volume=1001.,area=622.,
                       step_definition_key=('second.step','0:1:1:8',1))
       for _ in range(19)]
    # Forty occurrences exceed limit=4, but cost only two independent
    # definitions. The digests come from actual complete serialized B-Reps.
    result=prepare_occurrence_identities(a,b,limit=4)
    assert result['selected']==40
    assert result['proven']==40
    assert result['skipped']==0
    assert result['xcaf_reuse']>=38
    assert all(getattr(p,'_dscompare_normalized_digest',None) for p in a+b)


def test_large_independent_step_population_preserves_budget(monkeypatch):
    """Unknown/baked geometry cannot pretend to be a cheap shared XCAF part."""
    from types import SimpleNamespace
    from dsac29 import occurrence_identity as identity

    parts=[SimpleNamespace(volume=1001.,area=622.) for _ in range(40)]
    def should_not_serialize(*args,**kwargs):
        raise AssertionError('Independent over-budget B-Rep must not be serialized')
    monkeypatch.setattr(identity,'_canonical',should_not_serialize)
    result=prepare_occurrence_identities(parts,[],limit=4)
    assert result['selected']==40
    assert result['proven']==0
    assert result['skipped']==40


def test_xcaf_population_budget_remains_scoped_to_source_file(monkeypatch):
    """Identical label IDs in different STEP files still cost separate proofs."""
    from types import SimpleNamespace
    from dsac29 import occurrence_identity as identity

    shape=BRepPrimAPI_MakeBox(7.,11.,13.).Shape()
    parts=[SimpleNamespace(shape=shape,volume=1001.,area=622.,
                           step_definition_key=(f'source_{i}.step','0:1:1:8',1))
           for i in range(6) for _ in range(3)]
    def should_not_serialize(*args,**kwargs):
        raise AssertionError('Six different STEP files exceed the four-definition budget')
    monkeypatch.setattr(identity,'_canonical',should_not_serialize)
    result=prepare_occurrence_identities(parts,[],limit=4)
    assert result['selected']==18
    assert result['proven']==0
    assert result['skipped']==18
