from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL,TopAbs_FACE
from OCP.TopoDS import TopoDS,TopoDS_Shell,TopoDS_Compound
from OCP.BRep import BRep_Builder
from dsac29.closed_shell_import import recover
from dsac29.geometry import describe

def shell():return TopoDS.Shell_s(TopExp_Explorer(BRepPrimAPI_MakeBox(10,20,30).Shape(),TopAbs_SHELL).Current())
def test_closed_shell_recovered_without_shape_change():
    s=shell();r=recover(s)
    assert r is not None and abs(describe(r,'a','a').volume-6000)<1e-6
    assert recover(r) is None

def test_open_and_ambiguous_shells_are_not_closed_or_merged():
    builder=BRep_Builder();opened=TopoDS_Shell();builder.MakeShell(opened)
    it=TopExp_Explorer(shell(),TopAbs_FACE);it.Next()
    while it.More():builder.Add(opened,it.Current());it.Next()
    assert recover(opened) is None
    comp=TopoDS_Compound();builder.MakeCompound(comp);builder.Add(comp,shell());builder.Add(comp,shell())
    assert recover(comp) is None

def test_step_import_recovers_shell_and_preserves_name(tmp_path):
    from dsac29.step_io import ColoredDocument,load_step
    doc=ColoredDocument();doc.add(shell(),'Closed part',(.2,.3,.4));path=tmp_path/'shell.step'
    # Use native writer directly: report writer intentionally requires solids.
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    writer=STEPCAFControl_Writer();writer.SetNameMode(True);doc.tool.UpdateAssemblies()
    assert writer.Transfer(doc.doc);writer.Write(str(path))
    stats={};parts=load_step(str(path),diagnostics=stats)
    assert len(parts)==1 and parts[0].name=='Closed part'
    assert stats['recovered_closed_shell_occurrences']==1
