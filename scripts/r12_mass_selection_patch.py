"""DS Compare R12: reliable, high-contrast selection in mass-file queue."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'source'
p=root/'dsac29'/'gui_modern.py'
s=p.read_text(encoding='utf8')
def replace_once(old,new):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f'R12 patch anchor appears {n} times: {old[:95]!r}')
 s=s.replace(old,new,1)
replace_once(
 ' QWidget#mass-file-row[selected="true"]{background:SOFT;border:1px solid ACCENT;border-radius:9px;}\n QLabel#mass-row-label{background:transparent;}',
 ''' QWidget#mass-file-row[selected="true"]{background:ACCENT;border:1px solid ACCENT;border-radius:8px;}
 QLabel#mass-row-label{background:transparent;color:INK;}
 QLabel#mass-row-label[massSelected="true"]{background:transparent;color:#FFFFFF;font-weight:650;}
 QPushButton#delete-one[massSelected="true"]{background:transparent;color:#FFFFFF;border:0;}
 QPushButton#delete-one[massSelected="true"]:hover{background:#FFFFFF;color:#1268D8;border-radius:7px;}'''
)
import re
match=re.search(r'^class MassRowWidget\(QWidget\):.*?(?=^class ModernWindow\(PreviousWindow\):)',s,flags=re.M|re.S)
if not match:raise RuntimeError('R12 missing MassRowWidget class')
s=s[:match.start()]+'''class MassRowWidget(QWidget):
 """Clickable mass-list row with explicit, theme-safe selected background."""
 def __init__(self,owner,item):
  super().__init__()
  self._owner=owner
  self._item=item
  self.setAttribute(Qt.WA_StyledBackground,True)
 def paintEvent(self,event):
  # Explicit QWidget item-widget paint avoids lost QSS selection on Windows.
  dark=self._owner.theme.currentText()=='Ciemny'
  palette=DARK if dark else LIGHT
  selected=bool(self._item.isSelected())
  hover=self.underMouse() and not selected
  fill=QColor(palette['accent'] if selected else
              (palette['hover'] if hover else palette['field']))
  border=QColor(palette['accent'] if selected else palette['line'])
  painter=QPainter(self)
  painter.setRenderHint(QPainter.Antialiasing)
  painter.setPen(QPen(border,1.2))
  painter.setBrush(QBrush(fill))
  painter.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),7.5,7.5)
  painter.end()
 def enterEvent(self,event):
  self.update();super().enterEvent(event)
 def leaveEvent(self,event):
  self.update();super().leaveEvent(event)
 def mousePressEvent(self,event):
  if event.button()==Qt.LeftButton:
   self._owner._mass_toggle_row(self._item,event.modifiers())
   event.accept()
  else:super().mousePressEvent(event)

'''+s[match.end():]
replace_once("   label=QLabel(model.name);label.setObjectName('mass-row-label')",
             "   label=QLabel(model.name);label.setObjectName('mass-row-label')\n   label.setProperty('massSelected',False)")
replace_once("   delete.setFixedSize(26,26)\n   delete.setToolTip",
             "   delete.setFixedSize(26,26)\n   delete.setProperty('massSelected',False)\n   delete.setToolTip")
replace_once(
 '''   if holder.property('selected')!=selected:
    holder.setProperty('selected',selected)
    holder.style().unpolish(holder);holder.style().polish(holder)''',
 '''   if holder.property('selected')!=selected:
    holder.setProperty('selected',selected)
    holder.style().unpolish(holder);holder.style().polish(holder)
    # Explicitly recolor child widgets; Qt does not propagate QSS dynamic
    # parent selection to embedded QLabel/QPushButton automatically.
    for child in holder.findChildren(QLabel)+holder.findChildren(QPushButton):
     if child.objectName() in ('mass-row-label','delete-one'):
      child.setProperty('massSelected',selected)
      child.style().unpolish(child);child.style().polish(child)
      child.update()
    holder.update()'''
)
replace_once(
 "  self._refresh_action_icons(p['ink'],p['accent'])",
 "  self._refresh_action_icons(p['ink'],p['accent'])\n  if hasattr(self,'mass_input_list'):\n   self._update_mass_row_selection()\n   for i in range(self.mass_input_list.count()):\n    holder=self.mass_input_list.itemWidget(self.mass_input_list.item(i))\n    if holder is not None:holder.update()")
p.write_text(s,encoding='utf8')
(root/'R12_ZMIANY.txt').write_text(
 'DS Compare 1.0 R12\n'
 '- Niebieski pasek zaznaczenia całego wiersza w obu motywach.\n'
 '- Białe nazwy i przyciski usuwania zaznaczonych plików.\n'
 '- Własne rysowanie QWidget bez zależności od aktualizacji stylów QSS.\n'
 '- Ctrl/Shift, masowe usuwanie i silnik geometrii R11 pozostają bez zmian.\n',
 encoding='utf8')
print('R12 full-row selected paint patch PASS')
