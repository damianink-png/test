from pathlib import Path
p=Path(__file__).resolve().parents[1]/'source'/'dsac29'/'gui_modern.py'
s=p.read_text(encoding='utf-8')
def rep(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:110])
 s=s.replace(a,b,1)

rep(' QListWidget#mass-input-list{padding:5px;border:1px solid LINE;border-radius:12px;background:FIELD;outline:0;}',
    ' QListWidget#mass-input-list{padding:3px;border:1px solid LINE;border-radius:11px;background:SURFACE;outline:0;}\n'
    ' QListWidget#mass-input-list QScrollBar:vertical{background:SURFACE;border:0;width:7px;margin:3px 0;}\n'
    ' QListWidget#mass-input-list QScrollBar::handle:vertical{background:LINE;border-radius:3px;min-height:24px;}\n'
    ' QListWidget#mass-input-list QScrollBar::add-line:vertical,QListWidget#mass-input-list QScrollBar::sub-line:vertical{height:0;}\n'
    ' QListWidget#mass-input-list QScrollBar::add-page:vertical,QListWidget#mass-input-list QScrollBar::sub-page:vertical{background:transparent;}')
rep(' QWidget#mass-file-row{background:FIELD;border:1px solid transparent;border-radius:9px;}',
    ' QWidget#mass-file-row{background:FIELD;border:1px solid LINE;border-radius:8px;}')
rep(' QListWidget#mass-input-list::item{border:0;padding:0;margin:0;min-height:43px;background:transparent;}',
    ' QListWidget#mass-input-list::item{border:0;padding:0;margin:0;background:transparent;}')
rep('  self.mass_input_list.setSpacing(3)',
    '  self.mass_input_list.setSpacing(2)\n'
    '  self.mass_input_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)\n'
    '  self.mass_input_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)')
rep('  self.mass_input_list.setMinimumHeight(50);self.mass_input_list.setMaximumHeight(170)',
    '  self.mass_input_list.setMinimumHeight(42);self.mass_input_list.setMaximumHeight(176)')
rep('   self.mass_input_list.setFixedHeight(min(182,max(46,count*42+5)))',
    '   self.mass_input_list.setFixedHeight(min(176,8+count*36+max(0,count-1)*2))')
rep("   item.setToolTip(str(model));item.setSizeHint(QSize(20,45))\n"
    "   holder=QWidget();holder.setObjectName('mass-file-row')\n"
    "   holder.setMinimumHeight(41);holder.setProperty('selected',False)\n"
    "   line=QHBoxLayout(holder)\n"
    "   line.setContentsMargins(12,0,12,0);line.setSpacing(10)\n"
    "   line.setAlignment(Qt.AlignVCenter)\n"
    "   label=QLabel(model.name);label.setObjectName('mass-row-label')\n"
    "   label.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)\n"
    "   label.setMinimumHeight(36);label.setToolTip(str(model))\n"
    "   label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)\n"
    "   line.addWidget(label,1,Qt.AlignVCenter)\n"
    "   delete=QPushButton('×');delete.setObjectName('delete-one')\n"
    "   delete.setFixedSize(30,30)",
    "   item.setToolTip(str(model));item.setSizeHint(QSize(20,36))\n"
    "   holder=MassRowWidget(self,item);holder.setObjectName('mass-file-row')\n"
    "   holder.setFixedHeight(36);holder.setProperty('selected',False)\n"
    "   line=QHBoxLayout(holder)\n"
    "   line.setContentsMargins(10,0,5,0);line.setSpacing(6)\n"
    "   label=QLabel(model.name);label.setObjectName('mass-row-label')\n"
    "   label.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)\n"
    "   label.setAttribute(Qt.WA_TransparentForMouseEvents,True)\n"
    "   label.setToolTip(str(model))\n"
    "   label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)\n"
    "   line.addWidget(label,1,Qt.AlignVCenter)\n"
    "   delete=QPushButton('×');delete.setObjectName('delete-one')\n"
    "   delete.setFixedSize(26,26)")
rep("  self.mass_file.path.setText(str(self.mass_inputs[0]) if self.mass_inputs else '')\n"
    "  self._update_mass_file_visual()",
    "  self.mass_file.path.setText(str(self.mass_inputs[0]) if self.mass_inputs else '')\n"
    "  self._last_mass_selection=None\n"
    "  self._update_mass_file_visual()")
rep(' def _mass_remove_one(self,item):',
    ''' def _mass_toggle_row(self,item,modifiers):
  if self.process is not None:return
  index=self.mass_input_list.row(item)
  if index<0:return
  current=item.isSelected()
  if modifiers & Qt.ShiftModifier and self._last_mass_selection is not None:
   lo=min(self._last_mass_selection,index)
   hi=max(self._last_mass_selection,index)
   if not modifiers & Qt.ControlModifier:self.mass_input_list.clearSelection()
   for pos in range(lo,hi+1):self.mass_input_list.item(pos).setSelected(True)
  elif modifiers & Qt.ControlModifier:
   item.setSelected(not current)
   self._last_mass_selection=index
  else:
   self.mass_input_list.clearSelection()
   item.setSelected(not current)
   self._last_mass_selection=index
  self._update_mass_remove_button()

 def _mass_remove_one(self,item):''')
rep(' def _mass_add(self,paths):\n  known=',
    ' def _mass_add(self,paths):\n  if self.process is not None:return\n  known=')
rep(' def _mass_pick_files(self):\n  from PySide6.QtWidgets',
    ' def _mass_pick_files(self):\n  if self.process is not None:return\n  from PySide6.QtWidgets')
rep(' def _mass_pick_folder(self):\n  from PySide6.QtWidgets',
    ' def _mass_pick_folder(self):\n  if self.process is not None:return\n  from PySide6.QtWidgets')
rep(' def _mass_running_controls(self,busy):\n'
    '  for ctrl in (self.mass_add_files,self.mass_add_folder,self.mass_reset):\n'
    '   ctrl.setEnabled(not busy)\n'
    '  self.mass_remove_selected.setEnabled(not busy and bool(self.mass_input_list.selectedItems()))',
    ' def _mass_running_controls(self,busy):\n'
    '  for ctrl in (self.mass_add_files,self.mass_add_folder,self.mass_reset):\n'
    '   ctrl.setEnabled(not busy)\n'
    '  self.mass_drop.setBusy(busy)\n'
    '  self.mass_input_list.setEnabled(not busy)\n'
    '  self.mass_remove_selected.setEnabled(not busy and bool(self.mass_input_list.selectedItems()))')
rep("  for card in (self.a,self.b):\n"
    "   if hasattr(card,'_remove_model_button'):\n"
    "    card._remove_model_button.setEnabled(not busy)",
    "  for card in (self.a,self.b):\n"
    "   if hasattr(card,'_remove_model_button'):\n"
    "    card._remove_model_button.setEnabled(not busy)\n"
    "  if hasattr(self,'mass_drop'):self._mass_running_controls(busy)")
rep('class ModernWindow(PreviousWindow):',
    '''class MassRowWidget(QWidget):
 """A custom list-row surface with explicit selection forwarding."""
 def __init__(self,owner,item):
  super().__init__()
  self._owner=owner;self._item=item
 def mousePressEvent(self,event):
  if event.button()==Qt.LeftButton:
   self._owner._mass_toggle_row(self._item,event.modifiers())
   event.accept()
  else:super().mousePressEvent(event)

class ModernWindow(PreviousWindow):''')
p.write_text(s,encoding='utf-8')

p=Path(__file__).resolve().parents[1]/'source'/'dsac29'/'mass_drop.py'
s=p.read_text(encoding='utf-8')
def change(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a)
 s=s.replace(a,b,1)
change('        self._add_callback=add_callback\n        self.setObjectName',
       '        self._add_callback=add_callback\n        self._busy=False\n        self.setObjectName')
change('    def _active(self,value):',
       '    def setBusy(self,busy):\n        self._busy=bool(busy)\n        self.setAcceptDrops(not busy)\n        if busy:self._active(False)\n    def _active(self,value):')
change('    def dragEnterEvent(self,event):\n        paths',
       '    def dragEnterEvent(self,event):\n        if self._busy:\n            event.ignore();return\n        paths')
change('    def dragMoveEvent(self,event):\n        if self._paths',
       '    def dragMoveEvent(self,event):\n        if self._busy:\n            event.ignore();return\n        if self._paths')
change('    def dropEvent(self,event):\n        self._active(False)',
       '    def dropEvent(self,event):\n        self._active(False)\n        if self._busy:\n            event.ignore();return')
p.write_text(s,encoding='utf-8')
print('R10 Qt mass UI + DnD patch PASS')
