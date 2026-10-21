"""Windows CI smoke R11.22: batch mass, reset, native grouping and result buttons."""
from pathlib import Path
from tempfile import TemporaryDirectory
import csv,json,os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from dsac29.gui46 import Window
from dsac29.mass_batch import analyze_many

app=QApplication.instance() or QApplication([])
# Earlier R11.21 smoke enables flat mode and leaves its QSettings value behind.
QSettings('DSCompare','Revision45').remove('zw3d_flat_output_r1122')
w=Window()
assert w.zw3d_flat_output.isChecked() is False,'native subassemblies must be enabled by default'
assert w.mass_done.isHidden() and w.mass_actions.isHidden()
assert hasattr(w,'mass_add_folder') and hasattr(w,'mass_reset')
with TemporaryDirectory() as temp:
 folder=Path(temp)
 files=[]
 for index in (1,2):
  path=folder/f'Test_Model_{index}.stp'
  writer=STEPControl_Writer()
  writer.Transfer(BRepPrimAPI_MakeBox(10*index,10,10).Shape(),STEPControl_AsIs)
  assert writer.Write(str(path))==IFSelect_RetDone
  files.append(path)
 w._mass_add(files)
 assert len(w.mass_inputs)==2
 assert w.mass_file.path.text()==str(files[0])
 assert not w.mass_actions.isVisible()
 result,summary=analyze_many([str(p) for p in files],folder/'outputs',7850,progress=lambda s:None,max_solids=20000)
 assert summary['liczba_plikow']==2,summary
 assert summary['liczba_bryl']==2,summary
 assert summary['liczba_pozycji']==2,summary
 assert abs(summary['masa_calosci_kg']-0.02355)<0.0001,summary
 assert len(summary['modele'])==2
 assert (result/'RAPORT_MASY.html').is_file()
 assert (result/'MASY_PLIKI.csv').is_file()
 assert (result/'MASY_CZESCI.csv').is_file()
 for item in summary['modele']:
  assert (result/item['raport']).is_file(),item
 with (result/'MASY_CZESCI.csv').open(encoding='utf-8-sig',newline='') as stream:
  rows=list(csv.reader(stream,delimiter=';'))
 assert len(rows)==3,rows
 assert any('Test_Model_1.stp' in value for value in rows[1])
 assert any('Test_Model_2.stp' in value for value in rows[2])
 w._mass_reset()
 assert w.mass_inputs==[]
 assert w.mass_file.path.text()==''
 assert w.mass_input_list.count()==0
 assert w.mass_done.isHidden() and w.mass_actions.isHidden()
w.close()
print('PASS: R11.22 native groups default, multi-model summary/HTML/CSV, mass reset, final-only action visibility')
