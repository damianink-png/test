"""STEP round-trip: count, names, positions and fail-closed negative controls."""
import numpy as np
import pytest
from dataclasses import replace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.aligned_step_restart import save_aligned_step_and_reload, _match_imported


def _assembly():
    parts=[]
    for i in range(5):
        shape=BRepPrimAPI_MakeBox(10.+i, 15., 7.).Shape()
        original=describe(shape, 'plate' if i<3 else 'gusset',
                          f'ROOT/item_{i}', 'original.step')
        parts.append(_relocate(original,np.eye(3),
                               np.array([float(i*40+1200),-400.,200.])))
    return parts


def test_roundtrip_reimports_and_restores_metadata(tmp_path):
    parts=_assembly()
    result,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert path.is_file() and path.stat().st_size>500
    assert stats['solids_expected']==stats['solids_reimported']==len(parts)
    assert sorted(p.path for p in result)==sorted(p.path for p in parts)
    assert sorted(p.source for p in result)==sorted(p.source for p in parts)
    for a in parts:
        b=next(x for x in result if x.path==a.path)
        assert np.linalg.norm(a.center-b.center)<.001
        assert abs(a.volume-b.volume)<.001


def test_roundtrip_refuses_missing_occurrence():
    parts=_assembly()
    with pytest.raises(RuntimeError,match='liczba brył'):
        _match_imported(parts,parts[:-1],.01)


def test_roundtrip_refuses_wrong_geometry_metadata():
    parts=_assembly()
    changed=list(parts)
    changed[0]=replace(changed[0],volume=changed[0].volume+100)
    with pytest.raises(RuntimeError,match='brak jednoznacznie'):
        _match_imported(parts,changed,.01)


def test_roundtrip_repeated_shared_shape_with_distinct_occurrences(tmp_path):
    # Real CAD assemblies frequently reuse one shape definition many times.
    # Instance labels must survive STEPCAF deduplication without mispairing.
    shared=BRepPrimAPI_MakeBox(9.,9.,9.).Shape()
    parts=[]
    for i in range(12):
        original=describe(shared, f'M3 Heat Set:{i+1}',
                          f'ROOT/shared_insert_{i}', 'source.step')
        parts.append(_relocate(original,np.eye(3),
                               np.array([1000.+i*45.,-395.,210.])))
    result,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert stats['solids_expected']==stats['solids_reimported']==12
    assert sorted(x.name for x in result)==sorted(x.name for x in parts)
    assert sorted(x.path for x in result)==sorted(x.path for x in parts)
    for old in parts:
        new=next(x for x in result if x.path==old.path)
        assert np.linalg.norm(np.array(old.center)-np.array(new.center))<.001



@pytest.mark.parametrize('count',[12,50,120,200])
def test_roundtrip_repeated_identical_names_different_positions(tmp_path,count):
    # STEP assemblies may repeat both the geometry definition and occurrence name.
    shared=BRepPrimAPI_MakeBox(8., 12., 6.).Shape()
    parts=[]
    for i in range(count):
        original=describe(shared, 'M3 Heat Set:1',
                          f'ROOT/heat_set_{i}', 'source.step')
        parts.append(_relocate(original,np.eye(3),
                               np.array([150.+i*17., -30.+(i%3)*11., 40.])))
    restored,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert path.is_file()
    assert stats['solids_expected']==stats['solids_reimported']==count
    assert sorted(x.path for x in restored)==sorted(x.path for x in parts)
    for old in parts:
        new=next(x for x in restored if x.path==old.path)
        assert np.linalg.norm(np.array(old.center)-np.array(new.center))<.001
        assert abs(old.volume-new.volume)<.001


def test_roundtrip_permuted_import_order_is_bijective():
    parts=_assembly()
    matched=_match_imported(parts,list(reversed(parts)),0.01)
    assert [x.path for x in matched]==list(reversed([x.path for x in parts]))



def test_roundtrip_recovers_uniquely_renamed_imported_occurrence():
    parts=_assembly()
    imported=list(parts)
    imported[0]=replace(imported[0],name='STEPCAF shared definition label')
    restored=_match_imported(parts,imported,0.01)
    assert [p.name for p in restored]==[p.name for p in parts]
    assert [p.path for p in restored]==[p.path for p in parts]


def test_roundtrip_refuses_ambiguous_renamed_occurrence():
    shape=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    a=describe(shape,'occurrence A','ROOT/A','source.step')
    b=describe(shape,'occurrence B','ROOT/B','source.step')
    # Two co-located indistinguishable occurrences: scalar/spatial
    # invariants cannot determine which metadata belongs to the STEP part.
    renamed=replace(a,name='STEPCAF changed label')
    with pytest.raises(RuntimeError,match='brak jednoznacznie'):
        _match_imported([a,b],[renamed,b],0.01)



@pytest.mark.parametrize('offset', [
    (1., 0., 0.),
    (0., -100., 0.),
    (1000., 395., -210.),
    (-1275., 395., -210.),
])
def test_roundtrip_shifted_small_assembly(tmp_path, offset):
    # Verify physical STEP round-trip after four distinct global translations.
    base=_assembly()
    moved=[_relocate(p,np.eye(3),np.array(offset,dtype=float)) for p in base]
    restored,path,stats=save_aligned_step_and_reload(
        moved,tmp_path,0.01)
    assert path.is_file() and path.stat().st_size>500
    assert stats['solids_expected']==stats['solids_reimported']==len(base)
    for original in moved:
        imported=next(x for x in restored if x.path==original.path)
        assert np.linalg.norm(np.array(original.center)-np.array(imported.center))<.001
        assert abs(original.volume-imported.volume)<.001
        assert abs(original.area-imported.area)<.001



def test_roundtrip_refuses_ambiguous_same_name_coincident_occurrences():
    # Equal names and coincident identical solids must not silently assign
    # distinct source paths by arbitrary imported enumeration order.
    shape=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    first=describe(shape,'M3 Heat Set:1','ROOT/first','source.step')
    second=replace(first,path='ROOT/second')
    with pytest.raises(RuntimeError,match='brak jednoznacznie'):
        _match_imported([first,second],[first,second],0.01)


@pytest.mark.parametrize('count',[12,50,120,200])
def test_roundtrip_repeated_names_with_global_shift(tmp_path,count):
    # Combined shared-definition/duplicate-name/global-shift case.
    shared=BRepPrimAPI_MakeBox(9.,11.,7.).Shape()
    parts=[]
    offset=np.array([-1275.,395.,-210.])
    for i in range(count):
        part=describe(shared,'M3 Heat Set:1',
                      f'ROOT/insert_{i}','source.step')
        parts.append(_relocate(part,np.eye(3),
                               offset+np.array([float(i*30),float(i%5*18),0.])))
    restored,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert path.is_file() and path.stat().st_size>500
    assert stats['solids_expected']==stats['solids_reimported']==count
    assert {p.path for p in restored}=={p.path for p in parts}
    for old in parts:
        new=next(p for p in restored if p.path==old.path)
        assert np.linalg.norm(np.array(old.center)-np.array(new.center))<.001
        assert abs(old.volume-new.volume)<.001
        assert abs(old.area-new.area)<.001


def test_roundtrip_rejects_nonfinite_centroid_metadata():
    # A NaN centroid must never silently pass a distance threshold.
    parts=_assembly()
    corrupt=list(parts)
    corrupt[0]=replace(corrupt[0],center=(float('nan'),)+tuple(corrupt[0].center[1:]))
    with pytest.raises(RuntimeError):
        _match_imported(parts,corrupt,0.01)


def test_roundtrip_continues_with_native_imported_metadata_when_names_cannot_be_recovered(tmp_path,monkeypatch):
    # Real-user repro: manually comparing A with B_WYROWNANY.step works,
    # while attempting to restore old B names aborts before B-Rep comparison.
    import dsac29.aligned_step_restart as restart
    original_match=restart._match_imported
    def fail_metadata_only(original,imported,tolerance):
        raise RuntimeError('Wyrównany STEP: brak jednoznacznie odpowiadającego elementu 04244003_AF1')
    monkeypatch.setattr(restart,'_match_imported',fail_metadata_only)
    parts=_assembly()
    imported,path,stats=restart.save_aligned_step_and_reload(parts,tmp_path,.01)
    assert path.is_file()
    assert len(imported)==len(parts)
    assert stats['metadata_association']=='imported_step_native'
    assert '04244003_AF1' in stats['metadata_association_warning']
    # This must return independently imported STEP shapes, not pre-export B.
    assert all(a.shape is not b.shape for a,b in zip(parts,imported))
    monkeypatch.setattr(restart,'_match_imported',original_match)
