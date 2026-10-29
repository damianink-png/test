from openassembly.model import Part, _same_placement

def make(uid,center,extent,fp=("same",)):
    return Part(uid=uid,name="Idler_Gear:1",path=uid,volume=100,area=60,
                centroid=center,fingerprint=fp,pose=(1,0,0,0,1,0,0,0,1),
                extents=extent)

def test_missing_geometry_must_not_bypass_bbox_check():
    a=make("a",(0,0,0),(10,10,10))
    b=make("b",(0,0,0),(10,10,10.0737))
    assert not _same_placement(a,b,.01)

def test_real_translation_remains_moved():
    a=make("a",(0,0,0),(10,10,10))
    b=make("b",(17,-9,13),(10,10,10))
    assert not _same_placement(a,b,.01)

def test_different_geometry_still_checks_bbox():
    a=make("a",(0,0,0),(10,10,10),("one",))
    b=make("b",(0,0,0),(10,10,11.4),("two",))
    assert not _same_placement(a,b,.01)
