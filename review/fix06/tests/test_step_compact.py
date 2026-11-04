"""Compact STEP experiment: B-Rep and colors survive a full read-back."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from dsac29.step_io import ColoredDocument,load_step


def _export(path,mode,monkeypatch):
    monkeypatch.setenv('DSCOMPARE_STEP_PCURVES',mode)
    doc=ColoredDocument(group_by_status=True)
    doc.add(BRepPrimAPI_MakeCylinder(9.,25.).Shape(),'cylinder',(0.2,0.7,0.3),group='SAME',source_name='cylinder')
    doc.add(BRepPrimAPI_MakeBox(12.,15.,18.).Shape(),'box',(0.8,0.2,0.4),group='ADDED',source_name='box')
    stat=doc.write(path)
    assert stat['weryfikacja']=='pelna_ponowny_import'
    assert stat['pokolorowane_etykiety']==2
    assert stat['pokolorowane_powierzchnie']>0
    return stat


def _shapes(path):
    parts=load_step(str(path))
    assert len(parts)==2
    result=[]
    for p in parts:
        assert BRepCheck_Analyzer(p.shape).IsValid()
        faces=TopExp_Explorer(p.shape,TopAbs_FACE);n=0
        while faces.More():n+=1;faces.Next()
        result.append((round(float(p.volume),6),n))
    return sorted(result)


def test_compact_step_roundtrip_preserves_geometry_and_colors(tmp_path,monkeypatch):
    original=tmp_path/'normal.step';small=tmp_path/'compact.step'
    normal=_export(original,'on',monkeypatch)
    compact=_export(small,'off',monkeypatch)
    try:
        assert normal['krzywe_2d_step']=='zapisane'
        assert compact['krzywe_2d_step']=='pominiete'
        assert not normal['eksperymentalny_step_bez_pcurves']
        assert compact['eksperymentalny_step_bez_pcurves']
        assert b'PCURVE(' in original.read_bytes()
        assert b'PCURVE(' not in small.read_bytes()
        assert small.stat().st_size<original.stat().st_size
        assert _shapes(original)==_shapes(small)
    finally:
        monkeypatch.delenv('DSCOMPARE_STEP_PCURVES',raising=False)
        from OCP.Interface import Interface_Static
        Interface_Static.SetIVal_s('write.surfacecurve.mode',1)


def test_compact_step_flag_rejects_unknown_values(tmp_path,monkeypatch):
    monkeypatch.setenv('DSCOMPARE_STEP_PCURVES','automatic')
    doc=ColoredDocument(group_by_status=True)
    doc.add(BRepPrimAPI_MakeBox(10.,10.,10.).Shape(),'box',(0.2,0.7,0.3),group='SAME')
    import pytest
    with pytest.raises(ValueError,match='DSCOMPARE_STEP_PCURVES'):
        doc.write(tmp_path/'invalid.step')
    assert not (tmp_path/'invalid.step').exists()
