import json
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29.manual_pairs import apply_pairs
from dsac29.view_state import visible_version,opacity

def part(n):return describe(BRepPrimAPI_MakeBox(10+n,20,30).Shape(),'P','P')

@pytest.mark.parametrize('status,role,mode,expected',[
 ('SAME','B','A',True),('RENAMED','B','A',True),('ADDED','B','A',False),('REMOVED','A','B',False),
 ('CHANGED','A','A',True),('CHANGED','B','A',False),('CHANGED','A','B',False),('MOVED','B','B',True),('UNCERTAIN','A','A+B',True)])
def test_version_visibility(status,role,mode,expected):assert visible_version(status,role,mode)==expected

def test_dim_does_not_hide_or_reclassify_geometry():
 assert opacity('SAME','B','A',True)==.15
 assert opacity('CHANGED','A','A',True)==1
 assert opacity('CHANGED','A','A+B',False)==.25

def test_manual_pair_keeps_every_occurrence_and_marks_orphans():
 a=[part(0),part(1)];b=[part(1),part(0)]
 records=[Record(0,0,'UNCERTAIN',''),Record(1,1,'UNCERTAIN','')]
 r=apply_pairs(a,b,records,[[0,1]],.01)
 assert {(x.a_index,x.b_index,x.status) for x in r}=={(0,1,'SAME'),(1,None,'UNCERTAIN'),(None,0,'UNCERTAIN')}
 r=apply_pairs(a,b,records,[[0,1],[1,0]],.01)
 assert len(r)==2 and all(x.status=='SAME' for x in r)

def test_duplicate_manual_pair_rejected():
 with pytest.raises(ValueError):apply_pairs([part(0)],[part(0),part(1)],[],[[0,0],[0,1]],.01)

def test_manual_geometry_error_is_uncertain(monkeypatch):
 import dsac29.manual_pairs as m
 def fail(*args):raise RuntimeError('test')
 monkeypatch.setattr(m,'equivalent_world',fail)
 assert m.apply_pairs([part(0)],[part(0)],[],[[0,0]],.01)[0].status=='UNCERTAIN'

def test_source_change_blocks_review(tmp_path):
 from dsac29.cli import process
 from pathlib import Path
 source=Path(__file__).resolve().parents[1]/'samples'
 with pytest.raises(ValueError,match='zmieniły'):
  process(source/'MODEL_A.step',source/'MODEL_B.step',tmp_path,manual_review={'fingerprints':{'A':'wrong','B':'wrong'},'pairs':[]})

def test_unified_view_lists_changes_and_coverage(tmp_path,monkeypatch):
 from PySide6.QtWidgets import QApplication
 import dsac29.gui_qt37 as ui
 from dsac29.cli import process
 from pathlib import Path
 source=Path(__file__).resolve().parents[1]/'samples'
 folder,records,_=process(source/'MODEL_A.step',source/'MODEL_B.step',tmp_path/'result',step=False,diff_step=False,direct_scene=True,progress=None)
 monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
 app=QApplication.instance() or QApplication([]);w=ui.Window();w.result_dir=folder;w.load_summary()
 assert w.change_list.count()==sum(r.status!='SAME' for r in records)
 assert w.change_tabs.currentIndex()==0 and not w.inspector.isVisible()
 assert 'Błędy siatki: 0' in w.coverage_banner.text()
 assert w.version_mode.currentText()=='A+B'
 w.close()

def test_mode_switch_does_not_move_camera(tmp_path,monkeypatch):
 from PySide6.QtWidgets import QApplication
 import dsac29.gui_qt37 as ui
 from vtkmodules.vtkRenderingCore import vtkActor
 monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
 app=QApplication.instance() or QApplication([]);w=ui.Window()
 class Render:
  def Render(self):pass
 class Widget:
  def GetRenderWindow(self):return Render()
 class CameraGuard:
  def ResetCamera(self,*args):raise AssertionError('A/B switch must retain camera')
 w.vtk_widget=Widget();w.renderer=CameraGuard();w.viewer_ready=True;w.scene_is_result=True
 w.body_actors=[('[CHANGED] [R000000] P [A]',vtkActor()),('[CHANGED] [R000000] P [B]',vtkActor()),('[SAME] [R000001] Q [B]',vtkActor())]
 w.version_mode.setCurrentText('A');assert [a.GetVisibility() for _,a in w.body_actors]==[1,0,1]
 w.version_mode.setCurrentText('B');assert [a.GetVisibility() for _,a in w.body_actors]==[0,1,1]
 w.version_mode.setCurrentText('A+B');assert all(a.GetVisibility() for _,a in w.body_actors)
 w.close()

def test_manual_review_end_to_end(tmp_path):
 from dsac29.cli import process
 from pathlib import Path
 source=Path(__file__).resolve().parents[1]/'samples'
 folder,records,_=process(source/'MODEL_A.step',source/'MODEL_B.step',tmp_path/'first',step=False,diff_step=False,progress=None)
 summary=json.loads((folder/'PODSUMOWANIE.json').read_text())
 pair=next(r for r in records if r.status=='CHANGED')
 review={'fingerprints':summary['source_fingerprints'],'pairs':[[pair.a_index,pair.b_index]]}
 second,r,_=process(source/'MODEL_A.step',source/'MODEL_B.step',tmp_path/'second',step=False,diff_step=False,direct_scene=True,progress=None,manual_review=review)
 assert any(x.confidence=='Para użytkownika' and x.status=='CHANGED' for x in r)
 assert json.loads((second/'PODSUMOWANIE.json').read_text())['manual_pairs']==review['pairs']
 assert json.loads((second/'SCENA_DIAGNOSTYKA.json').read_text())['complete']
