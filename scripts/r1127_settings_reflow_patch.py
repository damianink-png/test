"""R11.27 small-window settings: two side-by-side cards must reflow vertically."""
import os
from pathlib import Path
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/gui_modern.py"
s=p.read_text("utf8")
def change(a,b):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f"R11.27 settings reflow anchor count={n}: {a[:90]!r}")
 s=s.replace(a,b,1)
change("  grid.addWidget(compare,0,0);grid.addWidget(report,0,1)",
 """  self._settings_grid=grid
  self._settings_compare_card=compare
  self._settings_report_card=report
  self._settings_stacked=False
  grid.addWidget(compare,0,0);grid.addWidget(report,0,1)""")
# ModernWindow resized by GUI46.Window.resizeEvent; Qt child resizing must
# also recompute settings card layout, not only the compare input grid.
anchor=" def _init_adaptive_window(self):"
addition=""" def resizeEvent(self,event):
  super().resizeEvent(event)
  if hasattr(self,'_settings_grid'):
   self._reflow_settings(event.size().width())

 def _reflow_settings(self,width):
  if not hasattr(self,'_settings_grid'):return
  narrow=width<1050
  if self._settings_stacked==narrow:return
  grid=self._settings_grid
  compare=self._settings_compare_card
  report=self._settings_report_card
  grid.removeWidget(compare)
  grid.removeWidget(report)
  if narrow:
   grid.addWidget(compare,0,0,1,1)
   grid.addWidget(report,1,0,1,1)
   grid.setColumnStretch(0,1);grid.setColumnStretch(1,0)
  else:
   grid.addWidget(compare,0,0,1,1)
   grid.addWidget(report,0,1,1,1)
   grid.setColumnStretch(0,1);grid.setColumnStretch(1,1)
  self._settings_stacked=narrow
  grid.invalidate()

"""
change(anchor,addition+anchor)
change("  self.move(rect.topLeft())","  self.move(rect.topLeft())\n  self._reflow_settings(self.width())")
# Before the first show initialize the grid layout in its appropriate mode;
# do not rely on a resizeEvent fired by the WM later.
p.write_text(s,encoding="utf8")
print("R11.27 settings cards now flow vertically below 1050 logical pixels")
