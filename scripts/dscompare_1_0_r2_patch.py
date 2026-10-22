"""DS Compare 1.0 R2: fix cross-tab progress, compact queue rows and small-window accessibility."""
from pathlib import Path
import os
root=Path(os.environ['DS_COMPARE_SOURCE'])
def update(rel,transform):
 p=root/rel;s=p.read_text('utf8');s=transform(s);p.write_text(s,encoding='utf8')
def sub(s,old,new):
 n=s.count(old)
 if n!=1:raise RuntimeError(f'Expected one R2 anchor, got {n}: {old[:85]!r}')
 return s.replace(old,new,1)
def legacy(s):
 return sub(s,"   self.compare_summary.setText('Analiza trwa…' if kind=='compare' else 'Obliczanie masy…')",
 """   # A mass analysis must NEVER overwrite the comparison page.
   if kind=='compare':
    self.compare_summary.setToolTip('')
    self.compare_summary.setText('Analiza trwa…')
   elif kind=='mass':
    self.mass_summary.setToolTip('')
    self.mass_summary.setText('Trwa obliczanie masy…')""")
update('dsac29/gui46.py',legacy)
def modern(s):
 s=sub(s,'import json, os, sys, math','import json, os, sys, math, time')
 s=sub(s,' QFrame#details{background:transparent;border:0;}',
 ''' QLabel#global-activity{color:ACCENT;font-size:12px;font-weight:600;min-height:25px;padding:2px 8px;background:SOFT;border-radius:8px;}
 QProgressBar#global-activity-progress{max-height:4px;min-height:4px;border-radius:2px;background:LINE;}
 QProgressBar#global-activity-progress::chunk{background:ACCENT;border-radius:2px;}
 QWidget#mass-file-row{background:FIELD;border:0;border-bottom:1px solid LINE;}
 QWidget#mass-file-row[selected="true"]{background:SOFT;}
 QLabel#mass-row-label{background:transparent;}
 QListWidget#mass-input-list{padding:0;border:1px solid LINE;border-radius:9px;background:FIELD;}
 QListWidget#mass-input-list::item{border:0;padding:0;margin:0;min-height:40px;}
 QListWidget#mass-input-list::item:selected{background:SOFT;}
 QPushButton#delete-one{background:transparent;border:0;border-radius:7px;color:MUTED;min-width:30px;max-width:30px;min-height:30px;max-height:30px;padding:0;font-size:20px;}
 QPushButton#delete-one:hover{background:HOVER;color:ACCENT;}
 QFrame#details{background:transparent;border:0;}''')
 s=sub(s,"  layout.insertWidget(0,self.brand_modern)", """  layout.insertWidget(0,self.brand_modern)
  self._global_status=QLabel('');self._global_status.setObjectName('global-activity')
  self._global_status.setMinimumWidth(100);self._global_status.setMaximumWidth(220)
  self._global_status.setAlignment(Qt.AlignCenter);self._global_status.hide()
  layout.insertWidget(1,self._global_status)
  self._global_progress=QProgressBar();self._global_progress.setObjectName('global-activity-progress')
  self._global_progress.setTextVisible(False);self._global_progress.setRange(0,0)
  self._global_progress.setFixedWidth(64);self._global_progress.hide()
  layout.insertWidget(2,self._global_progress)""")
 s=sub(s," def _set_busy_ui(self,busy):", """ def _refresh_global_activity(self):
  if not hasattr(self,'_global_status') or self.process is None:return
  kind='Porównywanie' if self.task=='compare' else 'Obliczanie masy'
  elapsed=int(max(0,time.monotonic()-getattr(self,'_activity_started',time.monotonic())))
  self._global_status.setText(f'{kind} · {elapsed//60}:{elapsed%60:02d}')
  source=self.log if self.task=='compare' else self.mass_log
  stage=source.document().lastBlock().text().strip()
  self._global_status.setToolTip((stage or 'Przetwarzanie modeli')[-220:])

 def _set_busy_ui(self,busy):""")
 s=sub(s,"  self._analysis_busy_banner.setVisible(bool(busy))","""  self._analysis_busy_banner.setVisible(bool(busy))
  self._global_status.setVisible(bool(busy))
  self._global_progress.setVisible(bool(busy))
  if busy:
   self._activity_started=time.monotonic()
   self._refresh_global_activity()""")
 s=sub(s,"  min_h=min(540,max(420,area.height()-64))","  min_h=min(740,max(480,area.height()-54))")
 s=sub(s,"  height=max(min_h,min(870,int(area.height()*.87)))","  height=max(min_h,min(870,int(area.height()*.92)))")
 s=sub(s,"  page.layout().setSizeConstraint(QLayout.SetMinimumSize)", """  page.layout().setSizeConstraint(QLayout.SetMinimumSize)
  wrapper.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
  wrapper.setMinimumSize(0,0)""")
 s=sub(s,"  self.mass_input_list=QListWidget()","""  self.mass_input_list=QListWidget()
  self.mass_input_list.setObjectName('mass-input-list')
  self.mass_input_list.setSpacing(0)""")
 s=sub(s,"  material_form.addRow('Materiał',self.materials)\n  material_form.addRow('Gęstość [kg/m³]',self.density)","""  for name,widget in (('Materiał',self.materials),('Gęstość [kg/m³]',self.density)):
   title=QLabel(name);title.setObjectName('material-field-label')
   title.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
   title.setMinimumHeight(42);title.setMinimumWidth(150)
   widget.setMinimumHeight(42)
   material_form.addRow(title,widget)""")
 s=sub(s,"   item.setToolTip(str(model));item.setSizeHint(QSize(20,34))","   item.setToolTip(str(model));item.setSizeHint(QSize(20,42))")
 s=sub(s,"   holder=QWidget()\n   line=QHBoxLayout(holder)\n   line.setContentsMargins(8,1,3,1);line.setSpacing(8)","""   holder=QWidget();holder.setObjectName('mass-file-row')
   holder.setMinimumHeight(40);holder.setProperty('selected',False)
   line=QHBoxLayout(holder)
   line.setContentsMargins(12,0,12,0);line.setSpacing(10)
   line.setAlignment(Qt.AlignVCenter)""")
 s=sub(s,"   label=QLabel(model.name);label.setToolTip(str(model))","""   label=QLabel(model.name);label.setObjectName('mass-row-label')
   label.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
   label.setMinimumHeight(36);label.setToolTip(str(model))""")
 s=sub(s,"   line.addWidget(label,1)\n   delete=QPushButton('×');delete.setObjectName('delete-one')","""   line.addWidget(label,1,Qt.AlignVCenter)
   delete=QPushButton('×');delete.setObjectName('delete-one')
   delete.setFixedSize(30,30)""")
 s=sub(s,"   line.addWidget(delete)\n   self.mass_input_list.setItemWidget(item,holder)","""   line.addWidget(delete,0,Qt.AlignVCenter)
   self.mass_input_list.setItemWidget(item,holder)""")
 s=sub(s,"  self._update_mass_file_visual()\n\n def _mass_remove_one","""  self._update_mass_file_visual()
  self._update_mass_row_selection()

 def _update_mass_row_selection(self):
  for index in range(self.mass_input_list.count()):
   item=self.mass_input_list.item(index)
   holder=self.mass_input_list.itemWidget(item)
   if holder is None:continue
   selected=bool(item.isSelected())
   if holder.property('selected')!=selected:
    holder.setProperty('selected',selected)
    holder.style().unpolish(holder);holder.style().polish(holder)

 def _mass_remove_one""")
 s=sub(s,"  self.mass_remove_selected.setEnabled(self.process is None and bool(self.mass_input_list.selectedItems()))","""  self.mass_remove_selected.setEnabled(self.process is None and bool(self.mass_input_list.selectedItems()))
  self._update_mass_row_selection()""")
 s=sub(s,"   self.mass_input_list.setFixedHeight(min(170,max(45,count*37+6)))","   self.mass_input_list.setFixedHeight(min(182,max(46,count*42+5)))")
 s=sub(s,"  super().poll()\n  if self.process is None:return","""  super().poll()
  if self.process is None:return
  self._refresh_global_activity()""")
 s=sub(s,"  self._bom_label.hide();self.reset_button.setEnabled(True)","""  self._bom_label.hide();self.reset_button.setEnabled(True)
  self.compare_summary.setToolTip('');self.mass_summary.setToolTip('')
  self._global_status.setToolTip('')""")
 s=sub(s,"  if self.task=='compare':\n   success=bool(getattr(self,'completion_ok',False) and self.results.get('compare'))\n   self._set_compare_result_state(success)","""  if self.task=='compare':
   success=bool(getattr(self,'completion_ok',False) and self.results.get('compare'))
   self._set_compare_result_state(success)
   if not success:self.compare_summary.setText('Nie udało się zakończyć porównania — zobacz komunikat błędu.')
  elif self.task=='mass' and not getattr(self,'completion_ok',False):
   self.mass_summary.setText('Obliczanie masy nie zostało ukończone.')""")
 return s
update('dsac29/gui_modern.py',modern)
print('DS Compare 1.0 R2: queue rows, labels, global activity, stale status fix, min-height + scrolling')
