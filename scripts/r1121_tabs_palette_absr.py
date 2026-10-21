"""R11.21: full-width navigation, non-scrolling palette and ABSR-free STEP mode."""
import json,os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
def patch(name,fn):
 p=root/name
 old=p.read_text('utf8')
 new=fn(old)
 assert new!=old,name
 p.write_text(new,encoding='utf8')
def modern(t):
 a="  self._topbar=bar\n"
 assert t.count(a)==1
 t=t.replace(a,a+"""  # Prevent first tab clipping at 125-200% DPI: navigation gets its own row.
  navhost=QFrame(self.centralWidget());navhost.setObjectName('navigation-row')
  navlayout=QHBoxLayout(navhost);navlayout.setContentsMargins(18,6,18,8);navlayout.setSpacing(9)
  for key in ('compare','mass','settings'):
   b=self.nav[key]
   layout.removeWidget(b);b.setParent(navhost)
   b.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
   b.setMinimumWidth(max(145,b.fontMetrics().horizontalAdvance(b.text())+75))
   b.setMinimumHeight(44)
   navlayout.addWidget(b,1)
  self.centralWidget().layout().insertWidget(1,navhost)
  self._navigation_host=navhost
""",1)
 a="  rp.addRow('Kolory modeli',self.color_editor)\n"
 assert t.count(a)==1
 t=t.replace(a,a+"""  self.zw3d_flat_output=QCheckBox('STEP bez pustych części ABSR (ZW3D 2019)')
  enabled=str(self.store.value('zw3d_flat_output_r1121','true')).lower() not in ('false','0','no')
  self.zw3d_flat_output.setChecked(enabled)
  self.zw3d_flat_output.setToolTip('Włączone: 1 STEP PRODUCT na 1 rzeczywistą bryłę, status w kolorach/nazwach/warstwach. Wyłączone: podzłożenia, które importer ZW3D może pokazywać jako ABSR.')
  self.zw3d_flat_output.toggled.connect(lambda checked:self.store.setValue('zw3d_flat_output_r1121',checked))
  rp.addRow(self.zw3d_flat_output)
""",1)
 a=" QFrame#topbar{border:0;border-bottom:1px solid LINE;background:SURFACE;border-radius:0;}"
 assert t.count(a)==1
 t=t.replace(a,a+"\n QFrame#navigation-row{border:0;border-bottom:1px solid LINE;background:SURFACE;border-radius:0;}",1)
 return t
def colour_dialog(t):
 start=t.index(' def edit_export_colors(self):\n')
 end=t.index(' def show_color_help(self):\n',start)
 # 9 choices -> 5 rows, 2 columns, no scrollbars.
 new=""" def edit_export_colors(self):
  dlg=QDialog(self);dlg.setWindowTitle('Kolory elementów wynikowego STEP')
  dlg.setStyleSheet(self.styleSheet())
  screen=QGuiApplication.screenAt(self.mapToGlobal(self.rect().center())) or QGuiApplication.primaryScreen()
  geo=screen.availableGeometry() if screen else None
  dlg.setMinimumWidth(560)
  dlg.resize(min(740,max(560,geo.width()-60 if geo else 740)),430)
  root=QVBoxLayout(dlg);root.setContentsMargins(17,13,17,13);root.setSpacing(9)
  note=QLabel('Kolory elementów STEP — kliknij próbkę, aby zmienić kolor.')
  note.setWordWrap(True);root.addWidget(note)
  grid=QGridLayout();grid.setHorizontalSpacing(12);grid.setVerticalSpacing(8)
  pending=dict(self.export_colors);swatches={}
  def choose(key):
   color=QColorDialog.getColor(QColor(pending[key]),dlg,'Kolor elementów')
   if color.isValid():
    pending[key]=color.name()
    swatches[key].setStyleSheet('background:'+color.name()+';border:1px solid #777;border-radius:6px;')
    swatches[key].setToolTip(color.name())
  for i,(key,caption,default) in enumerate(EXPORT_COLOR_CHOICES):
   col=(i%2)*2;row=i//2
   label=QLabel(caption);label.setWordWrap(True)
   grid.addWidget(label,row,col)
   chip=QPushButton();chip.setFixedSize(62,28)
   chip.setAccessibleName('Zmień: '+caption);chip.setToolTip(pending[key])
   chip.setStyleSheet('background:'+pending[key]+';border:1px solid #777;border-radius:6px;')
   chip.clicked.connect(lambda checked=False,k=key:choose(k))
   swatches[key]=chip
   grid.addWidget(chip,row,col+1)
  grid.setColumnStretch(0,1);grid.setColumnStretch(2,1)
  root.addLayout(grid);root.addStretch(1)
  actions=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
  actions.button(QDialogButtonBox.Ok).setText('Zapisz')
  actions.button(QDialogButtonBox.Cancel).setText('Anuluj')
  actions.accepted.connect(dlg.accept);actions.rejected.connect(dlg.reject)
  footer=QHBoxLayout()
  reset=button('Przywróć domyślne',lambda:None)
  def defaults():
   for key,caption,default in EXPORT_COLOR_CHOICES:
    pending[key]=default
    swatches[key].setStyleSheet('background:'+default+';border:1px solid #777;border-radius:6px;')
    swatches[key].setToolTip(default)
  reset.clicked.connect(defaults)
  footer.addWidget(reset);footer.addStretch();footer.addWidget(actions)
  root.addLayout(footer)
  if dlg.exec()==QDialog.Accepted:
   self.export_colors=pending
   for key,value in pending.items():self.store.setValue('export_color_'+key,value)

"""
 return t[:start]+new+t[end:]
def gui45(t):
 a="            if getattr(self,'zw3d_body_colors',False):args+=['--body-colors']"
 assert t.count(a)==1
 return t.replace(a,a+"\n            if getattr(self,'zw3d_flat_output',None) is not None and self.zw3d_flat_output.isChecked():args+=['--flat-zw3d']",1)
def worker(t):
 a="    p.add_argument('--safe-export',action='store_true',help='ZW3D-safe flat export (default)')"
 assert t.count(a)==1
 t=t.replace(a,a+"\n    p.add_argument('--flat-zw3d',action='store_true',help='Write solid-only flat STEP without ABSR assembly nodes')",1)
 a="            os.environ['DSCOMPARE_STEP_VERIFY']=ns.step_verify"
 assert t.count(a)==1
 return t.replace(a,a+"\n            os.environ['DSCOMPARE_FLAT_FALLBACK']='1' if ns.flat_zw3d else '0'",1)
patch('dsac29/gui_modern.py',modern)
patch('dsac29/gui46.py',colour_dialog)
patch('dsac29/gui45.py',gui45)
patch('dsac29/worker_v37.py',worker)
assert "flat=os.environ.get('DSCOMPARE_FLAT_FALLBACK','0')=='1'" in (root/'dsac29/step_io.py').read_text('utf8')
(root/'VERSION.txt').write_text('R11.21\n',encoding='utf8')
info=root/'build_info.json'
if info.is_file():
 data=json.loads(info.read_text('utf8'))
 data['version']='R11.21 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 data['step_mode']='flat ZW3D (ABSR-free) default; native assembly optional'
 info.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
print('R11.21 UI palette/nav and flat STEP mode installed')
