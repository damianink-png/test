"""R11.28: lock navigation and inputs while worker runs; preserve checked state;
safe shutdown that does not strand frozen PyInstaller child processes.
"""
import os,json
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
def transform(rel,fn):
 p=root/rel;s=p.read_text('utf8');updated=fn(s);p.write_text(updated,encoding='utf8')
def gui45(s):
 old="self.run_compare,self.run_mass,self.a,self.b,self.mass_file,self.pages['settings']"
 n=s.count(old)
 if n!=3:raise RuntimeError(f'Expected 3 start/failure/finished settings lock sites; found {n}')
 s=s.replace(old,"self.run_compare,self.run_mass,self.a,self.b,self.mass_file")
 start=s.index("    def closeEvent(self,event):")
 end=s.find("\n    def ",start+7)
 if end<0:end=len(s)
 orig=s[start:end]
 if "self.process.kill();self.process.waitForFinished(3000)" not in orig:
  raise RuntimeError('Unexpected closeEvent shutdown policy')
 revised='''    def closeEvent(self,event):
        # Do not kill a frozen onefile worker while Windows is still using
        # its extracted DLLs. Let the user cancel, then close AFTER QProcess
        # emits finished and has released resources.
        if self.process is not None:
            QMessageBox.information(
                self,'Analiza nadal trwa',
                'Poczekaj do końca analizy albo użyj przycisku „Anuluj”. '
                'Zamknięcie będzie możliwe po zakończeniu procesu. '
                'Chroni to pliki tymczasowe i już zapisane wyniki.')
            event.ignore()
            return
        self.timer.stop()
        self.save_settings()
        event.accept()
'''
 return s[:start]+revised+s[end:]
transform('dsac29/gui45.py',gui45)

def gui46(s):
 old="   if hasattr(self,'_extra_settings_card'):self.pages['settings'].setEnabled(False)"
 if old not in s:raise RuntimeError('Unknown GUI46 disabled-settings hook')
 return s.replace(old,
  "   # Do not gray out settings QScrollArea: Qt hides checked indicators when disabled.\n   # R11.28 disables navigation during a job instead.",1)
transform('dsac29/gui46.py',gui46)

def modern(s):
 old="""  self.centralWidget().layout().insertWidget(1,navhost)
  self._navigation_host=navhost"""
 new="""  self.centralWidget().layout().insertWidget(1,navhost)
  self._navigation_host=navhost
  self._analysis_busy_banner=QLabel(
   'Trwa analiza — poczekaj na zakończenie. Przełączanie zakładek i zmiana ustawień są chwilowo zablokowane. Możesz użyć „Anuluj”.')
  self._analysis_busy_banner.setObjectName('muted')
  self._analysis_busy_banner.setWordWrap(True)
  self._analysis_busy_banner.setAlignment(Qt.AlignCenter)
  self.centralWidget().layout().insertWidget(2,self._analysis_busy_banner)
  self._analysis_busy_banner.hide()"""
 if s.count(old)!=1:raise RuntimeError('topbar banner anchor changed')
 s=s.replace(old,new,1)
 anchor=" def _modern_compare(self):"
 if s.count(anchor)!=1:raise RuntimeError('busy helper insertion point changed')
 code=""" def _set_busy_ui(self,busy):
  self._analysis_busy_banner.setVisible(bool(busy))
  for button in self.nav.values():
   button.setEnabled(not busy)
   button.setToolTip('Poczekaj na zakończenie analizy' if busy else '')
  for control in (self.theme_button,self.about_button,
                  self.output_button,self.color_editor):
   control.setEnabled(not busy)
  self._add_material_button.setEnabled(not busy)
  if hasattr(self,'mass_add_files'):self.mass_add_files.setEnabled(not busy)
  if hasattr(self,'mass_add_folder'):self.mass_add_folder.setEnabled(not busy)
  if hasattr(self,'mass_remove_selected'):
   self.mass_remove_selected.setEnabled(not busy and bool(self.mass_input_list.selectedItems()))
  if hasattr(self,'mass_reset'):self.mass_reset.setEnabled(not busy)

 def navigate(self,key):
  if self.process is not None and key!=self.task:
   # Programmatic and keyboard navigation are frozen as well as mouse tabs.
   return
  return super().navigate(key)

"""
 s=s.replace(anchor,code+anchor,1)
 old="""  super().start(kind)
  if kind=='mass' and self.process is not None:"""
 new="""  super().start(kind)
  if self.process is not None:self._set_busy_ui(True)
  if kind=='mass' and self.process is not None:"""
 if s.count(old)!=1:raise RuntimeError('modern start anchor')
 s=s.replace(old,new,1)
 old="""  super().finished(code,status)
  self.progress.hide();self.mass_progress.hide();self.report_progress.hide()"""
 new="""  try:
   super().finished(code,status)
  finally:
   self._set_busy_ui(False)
  self.progress.hide();self.mass_progress.hide();self.report_progress.hide()"""
 if s.count(old)!=1:raise RuntimeError('modern finished anchor')
 s=s.replace(old,new,1)
 return s
transform('dsac29/gui_modern.py',modern)
(root/'VERSION.txt').write_text('R11.28'+chr(10),encoding='utf8')
build=root/'build_info.json'
if build.exists():
 d=json.loads(build.read_text('utf8'))
 d['version']='R11.28 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 d['ui']='Responsive compare/mass, frozen tabs and settings during worker, controlled shutdown'
 d['alignment']='Verified B-to-A registration; ambiguous alignment fails closed'
 build.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('R11.28 UI: disabled nav and controls, permanent busy banner, preserved checkbox state, no unsafe kill during close')
