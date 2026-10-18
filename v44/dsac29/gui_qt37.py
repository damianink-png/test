"""DS Compare V3.7: responsive Qt dashboard with embedded VTK 3D model viewer.

CAD operations run in a separate process, never on the Qt GUI thread.
"""
from __future__ import annotations
import csv,json,os,sys
from pathlib import Path
from collections import Counter
from PySide6.QtCore import Qt,QProcess,QTimer,QUrl,QSettings,QSize
from PySide6.QtGui import QIcon,QColor,QDesktopServices,QFont,QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray,QRectF
from datetime import datetime
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QHBoxLayout,QVBoxLayout,
    QGridLayout,QStackedWidget,QLabel,QPushButton,QLineEdit,QFileDialog,QCheckBox,
    QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QTextEdit,QSplitter,QColorDialog,
    QTreeWidget,QTreeWidgetItem,QTabWidget,QListWidget,QListWidgetItem,QInputDialog,QMessageBox,QScrollArea,QAbstractItemView,QProgressBar,QSizePolicy,QButtonGroup)

COLORS={'SAME':'#9199A6','RENAMED':'#9199A6','MOVED':'#1FA6D9',
        'CHANGED':'#6659D4','ADDED':'#26D959','REMOVED':'#F23B33','UNCERTAIN':'#FFc726'}
STATUS_NAMES={'SAME':'Bez zmian','RENAMED':'Nowa nazwa','ADDED':'Nowe','CHANGED':'Geometria',
              'MOVED':'Położenie / obrót','REMOVED':'Usunięte','UNCERTAIN':'Do sprawdzenia'}
TABS=[('start','Przegląd','home'),('compare','Opcje analizy','compare'),('viewer','Model A / B','cube'),
      ('results','Wyniki','list'),('mass','Masa części','mass'),('settings','Ustawienia','settings')]
ICON_PATHS={
 'home':'<path d="M3 11 12 3 21 11M5 10v11h5v-7h4v7h5V10"/>',
 'compare':'<path d="M3 7h17l-4-4M21 17H4l4 4M20 7l-4 4M4 17l4-4"/>',
 'cube':'<path d="m12 2 9 5v10l-9 5-9-5V7zM3 7l9 5 9-5M12 12v10M7 5l10 5"/>',
 'list':'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
 'mass':'<path d="M8 7h8l4 14H4z"/><circle cx="12" cy="4" r="3"/>',
 'settings':'<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
 'theme':'<circle cx="12" cy="12" r="8"/><path d="M12 4v16"/>',
 'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
}
def menu_icon(key,color='#ACB5C9'):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICON_PATHS[key]}</g></svg>'
    renderer=QSvgRenderer(QByteArray(svg.encode()))
    pix=QPixmap(72,72);pix.fill(Qt.transparent);pix.setDevicePixelRatio(3)
    painter=QPainter(pix);renderer.render(painter,QRectF(0,0,24,24));painter.end()
    return QIcon(pix)

def _settings_path():
    root=Path(os.getenv('APPDATA') or (Path.home()/'.config'))
    return root/'DSCompare'/'ustawienia_v37.json'

def load_settings():
    try:return json.loads(_settings_path().read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def save_settings(settings):
    path=_settings_path();path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(settings,indent=2,ensure_ascii=False),encoding='utf-8')

def theme_qss(light=False):
    bg='#EEF2F6' if light else '#101722'
    card='#FFFFFF' if light else '#192330'
    inp='#F7F9FC' if light else '#121C29'
    text='#22263A' if light else '#F3F5FB'
    muted='#677087' if light else '#ACB5C9'
    edge='#DCE1EA' if light else '#2B3A4D'
    side='#E5E7EB' if light else '#0B121C'
    selection='#FFF0DC' if light else '#57422C'
    hover='#D6DDE7' if light else '#384157'
    return f'''
    QWidget#root {{background:{bg};color:{text};font-family:'Segoe UI';font-size:13px;}}
    QFrame#sidebar {{background:{side};border:none;border-radius:14px;}}
    QFrame#card,QFrame#panel {{background:{card};border:1px solid {edge};border-radius:12px;}}
    QFrame#colorcard {{background:{card};border:1px solid {edge};border-radius:14px;}}
    QLabel {{color:{text};background:transparent;}}
    QLabel#muted {{color:{muted};font-size:12px;}}
    QLabel#title {{color:{text};font-size:25px;font-weight:700;}}
    QLabel#section {{color:{text};font-size:16px;font-weight:700;}}
    QLabel#big {{color:{text};font-size:27px;font-weight:700;}}
    QLabel#kpi {{color:{text};font-size:24px;font-weight:700;}}
    QLabel#brand {{color:{text};font-size:18px;font-weight:800;}}
    QPushButton {{background:{card};border:1px solid {edge};border-radius:10px;color:{text};padding:10px 15px;font-weight:600;}}
    QPushButton:hover {{background:{hover};border:1px solid #F4A340;}}
    QPushButton:pressed {{background:{selection};}}
    QPushButton:disabled {{color:{muted};background:{inp};}}
    QPushButton#nav {{background:transparent;border:none;text-align:left;border-radius:10px;padding:13px 14px;}}
    QPushButton#nav:hover {{background:{hover};}}
    QPushButton#nav[active="true"] {{background:{selection};color:{'#99530A' if light else '#FFD5A0'};font-weight:800;}}
    QPushButton#primary {{background:#F59E38;color:#241B11;border:none;border-radius:11px;font-weight:800;}}
    QPushButton#primary:hover {{background:#FFB85F;}}
    QPushButton#coral {{background:#FE7774;color:#261D25;border:none;font-weight:800;}}
    QPushButton#coral:hover {{background:#FF9A98;}}
    QPushButton#teal {{background:#F59E38;color:#241B11;border:none;font-weight:800;}}
    QPushButton#teal:hover {{background:#FFB85F;}}
    QPushButton#subtle {{background:transparent;border:1px solid {edge};}}
    QLineEdit,QComboBox,QTextEdit {{background:{inp};color:{text};border:1px solid {edge};border-radius:10px;padding:10px 12px;selection-background-color:#F59E38;}}
    QLineEdit:focus,QComboBox:focus {{border:1px solid #F59E38;}}
    QCheckBox {{color:{text};spacing:8px;}}
    QCheckBox::indicator {{width:16px;height:16px;}}
    QListWidget,QTreeWidget,QTableWidget {{background:{card};alternate-background-color:{inp};gridline-color:{edge};color:{text};border:0;border-radius:8px;selection-background-color:{selection};selection-color:{text};}}
    QHeaderView::section {{background:{inp};color:{muted};padding:11px;border:none;border-bottom:1px solid {edge};font-weight:700;}}
    QTableWidget::item {{padding:6px;}}
    QListWidget::item {{padding:12px 8px;border-bottom:1px solid {edge};}}
    QTabWidget::pane {{border:0;background:{card};}}
    QTabBar::tab {{background:{inp};color:{muted};padding:10px 12px;border-bottom:2px solid transparent;}}
    QTabBar::tab:selected {{color:{text};border-bottom:2px solid #F59E38;}}
    QProgressBar {{background:{inp};color:{text};border:1px solid {edge};border-radius:6px;min-height:17px;max-height:19px;text-align:center;font-weight:700;}}
    QProgressBar::chunk {{background:#F59E38;border-radius:5px;}}
    QComboBox::drop-down {{border:none;width:28px;}}
    QScrollBar:vertical {{background:transparent;width:9px;}}
    QScrollBar::handle:vertical {{background:{edge};border-radius:4px;min-height:22px;}}
    '''


def _label(text, kind=None):
    l=QLabel(text)
    if kind:l.setObjectName(kind)
    return l

def _panel(parent=None):
    f=QFrame(parent);f.setObjectName('card');return f

def _button(text,action=None,kind=None):
    b=QPushButton(text)
    if kind:b.setObjectName(kind)
    b.setMinimumHeight(39)
    if action:b.clicked.connect(action)
    return b

class StepDropEdit(QLineEdit):
    def __init__(self,*args):
        super().__init__(*args);self.setAcceptDrops(True)
        self.setPlaceholderText('Przeciągnij STEP lub wybierz plik…')
    def dragEnterEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in ('.step','.stp'):event.acceptProposedAction()
        else:event.ignore()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in ('.step','.stp'):
            self.setText(urls[0].toLocalFile());event.acceptProposedAction()
        else:event.ignore()

class Window(QMainWindow):
    def __init__(self, model_a='',model_b=''):
        super().__init__()
        self.settings=load_settings()
        self.settings.setdefault('motyw','ciemny')
        self.settings.setdefault('kolory',dict(COLORS))
        if self.settings.get('palette_version',0)<42:
            for key in ('ADDED','MOVED','UNCERTAIN'):self.settings['kolory'][key]=COLORS[key]
            self.settings['palette_version']=42
        self._sync_status_colors()
        self.setWindowTitle('DS Compare — porównywanie złożeń i geometrii')
        self.resize(1440,900);self.setMinimumSize(1100,700)
        img=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'assets'/'DSCompare.ico'
        if img.exists():self.setWindowIcon(QIcon(str(img)))
        self.process=None;self.worker_dir=None;self.worker_kind=None;self.worker_position=0
        self.result_dir=Path(self.settings.get('ostatni_wynik') or (Path.home()/'Documents'/'DSCompare'/'Wyniki'))
        self.viewer_actors={};self.viewer_ready=False
        self.root=QWidget();self.root.setObjectName('root');self.setCentralWidget(self.root)
        self.outer=QHBoxLayout(self.root);self.outer.setContentsMargins(15,15,15,15);self.outer.setSpacing(16)
        self.build_sidebar()
        self.stack=QStackedWidget();self.outer.addWidget(self.stack,1)
        self.pages={}
        for key,_,_ in TABS:
            w=QWidget();self.pages[key]=w;self.stack.addWidget(w)
        self.build_start();self.build_compare(model_a,model_b);self.build_viewer();self.build_results();self.build_mass();self.build_settings()
        self.set_theme(self.settings['motyw'],persist=False)
        self.navigate('viewer')
        if self.result_dir.exists():self.load_summary()

    def _sync_status_colors(self):
        p=self.settings['kolory']
        for key in COLORS:
            if not isinstance(p.get(key),str) or not QColor(p[key]).isValid():
                p[key]=COLORS[key]
        p['RENAMED']=p['SAME']


    def build_sidebar(self):
        self.side=QFrame();self.side.setObjectName('sidebar');self.side.setFixedWidth(206)
        self.outer.addWidget(self.side)
        lay=QVBoxLayout(self.side);lay.setContentsMargins(16,25,16,20);lay.setSpacing(6)
        logo=QHBoxLayout();logo.setSpacing(9)
        emblem=_label('◈');emblem.setStyleSheet('color:#F59E38;font-size:31px;font-weight:900')
        logo.addWidget(emblem)
        label=_label('DS Compare','brand');logo.addWidget(label);logo.addStretch()
        lay.addLayout(logo)
        edition=_label('4.4  /  PORÓWNANIE B-REP','muted');lay.addWidget(edition)
        lay.addSpacing(20)
        self.nav={}
        for key,name,icon in TABS:
            btn=_button('  '+name,lambda checked=False,k=key:self.navigate(k),'nav')
            btn.setIcon(menu_icon(icon));btn.setIconSize(QSize(26,26));btn.setFixedHeight(52)
            btn.setToolTip(name);btn.setAccessibleName(name)
            btn.setCursor(Qt.PointingHandCursor)
            lay.addWidget(btn);self.nav[key]=btn
        lay.addStretch()
        self.theme_sidebar=_button('Zmień motyw',self.toggle_theme,'subtle');self.theme_sidebar.setIcon(menu_icon('theme'));self.theme_sidebar.setIconSize(QSize(24,24))
        lay.addWidget(self.theme_sidebar)
        about=_button('O programie',self.show_about,'nav');about.setIcon(menu_icon('info'));about.setIconSize(QSize(24,24));lay.addWidget(about)

    def top(self,key,title,subtitle):
        page=self.pages[key]
        v=QVBoxLayout(page);v.setContentsMargins(2,4,2,4);v.setSpacing(17)
        row=QHBoxLayout();txt=QVBoxLayout();txt.setSpacing(5)
        txt.addWidget(_label(title,'title'));txt.addWidget(_label(subtitle,'muted'))
        row.addLayout(txt);row.addStretch()
        v.addLayout(row)
        return v

    def build_start(self):
        v=self.top('start','Centrum porównania','Twoje modele, analiza geometrii i wyniki w jednym miejscu')
        row=QHBoxLayout();row.setSpacing(15)
        for name,sub,obj,func in [('Porównaj modele','Złożenie A i B','coral',lambda:self.navigate('compare')),
                                  ('Otwórz podgląd','Obracaj modele 3D','teal',lambda:self.navigate('viewer')),
                                  ('Policz masę','Jeden model STEP','primary',lambda:self.navigate('mass'))]:
            tile=_panel();tl=QVBoxLayout(tile);tl.setContentsMargins(18,18,18,18)
            tl.addWidget(_label(name,'section'));tl.addWidget(_label(sub,'muted'));tl.addStretch()
            tl.addWidget(_button('Otwórz   →',func,obj));row.addWidget(tile,1)
        v.addLayout(row,2)
        v.addWidget(_label('Ostatnia analiza','section'))
        self.dashboard_kpi=QHBoxLayout()
        for k,name,color in [('SAME','Bez zmian','#9199A6'),('CHANGED','Nowe / zmienione','#6659D4'),('REMOVED','Usunięte','#F23B33')]:
            tile=_panel();t=QVBoxLayout(tile);t.setContentsMargins(16,14,16,14)
            num=_label('—','kpi');num.setStyleSheet(f'color:{color}')
            setattr(self,'kpi_'+k,num)
            t.addWidget(num);t.addWidget(_label(name,'muted'));self.dashboard_kpi.addWidget(tile,1)
        v.addLayout(self.dashboard_kpi,1)
        helpbox=_panel();h=QVBoxLayout(helpbox);h.setContentsMargins(20,18,20,18)
        h.addWidget(_label('Geometria bez zewnętrznego CAD','section'))
        h.addWidget(_label('Podgląd 3D działa w aplikacji. Dokładność porównania zapewnia silnik Open CASCADE; widok 3D wykorzystuje siatkę VTK.','muted'))
        h.addWidget(_label('STEP może zawierać kolory, ale ZW3D i CADbro mogą interpretować style inaczej. Wynik zawiera diagnostykę kolorów.','muted'))
        v.addWidget(helpbox,1)
        v.addStretch(1)

    def _file_line(self,title,initial='',folder=False):
        col=QVBoxLayout();col.setSpacing(6);col.addWidget(_label(title,'muted'))
        row=QHBoxLayout();entry=QLineEdit(initial) if folder else StepDropEdit(initial);entry.setClearButtonEnabled(True)
        btn=_button('Wybierz…')
        def pick():
            path=QFileDialog.getExistingDirectory(self,'Wybierz folder',entry.text()) if folder else QFileDialog.getOpenFileName(self,'Otwórz STEP',entry.text(),'Model STEP (*.step *.stp)')[0]
            if path:entry.setText(path)
        btn.clicked.connect(pick)
        row.addWidget(entry,1);row.addWidget(btn);col.addLayout(row)
        return col,entry

    def build_compare(self,a,b):
        v=self.top('compare','Porównanie modeli','Dokładna analiza B-Rep z podglądem wyników w aplikacji')
        p=_panel();pl=QVBoxLayout(p);pl.setContentsMargins(22,19,22,19);pl.setSpacing(15)
        r,self.file_a=self._file_line('MODEL A · wersja poprzednia',a);pl.addLayout(r)
        r,self.file_b=self._file_line('MODEL B · wersja nowa',b);pl.addLayout(r)
        r,self.file_out=self._file_line('KATALOG WYNIKÓW',str(self.result_dir),True);pl.addLayout(r)
        line=QHBoxLayout();line.setSpacing(15)
        line.addWidget(_label('Tolerancja [mm]','muted'))
        self.tolerance=QLineEdit('0,01');self.tolerance.setToolTip('Próg numeryczny dopasowania B-Rep. Nie jest pomiarem maksymalnej odchyłki powierzchni.');self.tolerance.setMaximumWidth(100);line.addWidget(self.tolerance)
        line.addWidget(_label('Gęstość [kg/m³]','muted'))
        self.density=QLineEdit('7850');self.density.setMaximumWidth(112);line.addWidget(self.density)
        line.addWidget(_label('STEP:','muted'))
        self.schema=QComboBox();self.schema.addItems(['AP214IS','AP242DIS']);self.schema.setCurrentText(self.settings.get('step_schema','AP214IS'));line.addWidget(self.schema)
        line.addStretch();pl.addLayout(line)
        opt=QHBoxLayout();opt.setSpacing(16)
        self.write_step=QCheckBox('Kolorowy STEP');self.write_step.setChecked(False);opt.addWidget(self.write_step)
        self.make_diff=QCheckBox('Różnice materiału (wolniej)');self.make_diff.setChecked(False);opt.addWidget(self.make_diff)
        opt.addStretch();pl.addLayout(opt)
        self.align_models=QCheckBox('Pomiń zmianę układu całego złożenia — wyrównaj B do A')
        self.align_models.setToolTip('Wymaga jednoznacznych wspólnych części. Zapisuje transformację w PODSUMOWANIE.json; pliki źródłowe pozostają bez zmian.')
        pl.addWidget(self.align_models)
        p.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum);v.addWidget(p)
        bar=QHBoxLayout()
        self.btn_compare=_button('▶  Rozpocznij porównanie',self.start_compare,'primary');bar.addWidget(self.btn_compare)
        self.btn_cancel=_button('Anuluj',self.cancel);self.btn_cancel.setEnabled(False);bar.addWidget(self.btn_cancel)
        bar.addStretch();bar.addWidget(_button('Otwórz folder wyników',self.open_folder,'subtle'))
        bar.addWidget(_button('⇄ Zamień A i B',self.swap_models))
        v.addLayout(bar)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);self.progress.setMinimumHeight(20);self.progress.setTextVisible(False);v.addWidget(self.progress)
        self.log=QTextEdit();self.log.setReadOnly(True);self.log.setPlaceholderText('Tutaj pojawią się informacje o postępie analizy…')
        self.log.setMinimumHeight(120);v.addWidget(self.log,1)
        self.status=_label('Gotowy do analizy','muted');v.addWidget(self.status)

    def build_viewer(self):
        v=self.top('viewer','Porównanie A / B','Wybierz zmianę po lewej, obejrzyj obie wersje w tym samym widoku')
        files=QHBoxLayout()
        for label,source in [('A',self.file_a),('B',self.file_b)]:
            files.addWidget(_label(label,'section'));edit=StepDropEdit(source.text());files.addWidget(edit,1)
            edit.textChanged.connect(source.setText);source.textChanged.connect(edit.setText)
            def choose(checked=False,target=edit):
                path=QFileDialog.getOpenFileName(self,'Wybierz model',target.text(),'STEP (*.step *.stp)')[0]
                if path:target.setText(path)
            button=_button('…',choose);button.setMaximumWidth(40);files.addWidget(button)
        self.quick_compare=_button('Porównaj',self.start_compare,'primary');files.addWidget(self.quick_compare)
        files.addWidget(_button('Opcje',lambda:self.navigate('compare'),'subtle'));v.addLayout(files)
        self.advanced_view=QWidget();toolbar=QHBoxLayout(self.advanced_view);toolbar.setContentsMargins(0,0,0,0);toolbar.addWidget(_label('Model:','muted'))
        self.viewer_model=QComboBox()
        self.viewer_model.addItems(['Własny STEP','Wynik porównania','Model A','Model B','Różnice materiału'])
        self.viewer_model.setCurrentIndex(1)
        self.viewer_model.setMinimumWidth(160);toolbar.addWidget(self.viewer_model)
        toolbar.addWidget(_label('Szczegółowość:','muted'))
        self.viewer_quality=QComboBox();self.viewer_quality.addItems(['szybka','normalna','dokladna']);self.viewer_quality.setCurrentIndex(1)
        toolbar.addWidget(self.viewer_quality)
        self.mesh_button=_button('Załaduj model 3D',self.start_mesh,'primary');toolbar.addWidget(self.mesh_button)
        toolbar.addStretch()
        toolbar.addWidget(_button('Dopasuj model',self.fit_model))
        v.addWidget(self.advanced_view);self.advanced_view.hide()
        self.custom_source_row=QWidget();own=QHBoxLayout(self.custom_source_row);own.setContentsMargins(0,0,0,0)
        own.addWidget(_label('Własny STEP:','muted'))
        self.viewer_custom_path=QLineEdit(self.settings.get('ostatni_podglad',''))
        self.viewer_custom_path.setPlaceholderText('Dowolny plik STEP/STP bez porównania')
        self.viewer_custom_path.textEdited.connect(lambda _:self.viewer_model.setCurrentIndex(0))
        own.addWidget(self.viewer_custom_path,1)
        own.addWidget(_button('Przeglądaj STEP…',self.choose_viewer_file,'subtle'))
        v.addWidget(self.custom_source_row)
        self.viewer_model.currentIndexChanged.connect(lambda index:self.custom_source_row.setVisible(index==0 and self.advanced_view.isVisible()))
        self.custom_source_row.setVisible(self.viewer_model.currentIndex()==0)
        self.viewer_progress=QProgressBar()
        self.viewer_progress.setTextVisible(False)
        self.viewer_progress.hide()
        v.addWidget(self.viewer_progress)
        legend=QHBoxLayout();self.legend_filters={}
        legend.addWidget(_label('Kolory:','muted'))
        for code,name in [(k,STATUS_NAMES[k]) for k in ('SAME','ADDED','CHANGED','MOVED','REMOVED','UNCERTAIN')]:
            cb=QCheckBox(name);cb.setChecked(self.settings.get('widoczne_statusy',{}).get(code,True))
            cb.toggled.connect(self.refresh_legend)
            self.legend_filters[code]=cb;legend.addWidget(cb)
        legend.addStretch();v.addLayout(legend)
        controls=QHBoxLayout()
        controls.addWidget(_button('Dopasuj model',self.fit_model))
        controls.addWidget(_button('Pokaż wszystkie',self.show_all_parts))
        controls.addWidget(_button('Tylko zaznaczona',self.isolate_part))
        controls.addWidget(_button('◀ Poprzednia zmiana',lambda:self.next_change(-1)))
        controls.addWidget(_button('Następna zmiana ▶',lambda:self.next_change(1)))
        self.old_visible=QCheckBox('Poprzednia geometria A');self.old_visible.setChecked(True);self.old_visible.toggled.connect(self.refresh_legend)
        v.addLayout(controls)
        visibility=QHBoxLayout();self.old_visible.hide()
        self.show_edges=QCheckBox('Krawędzie');self.show_edges.setChecked(False);self.show_edges.toggled.connect(self.toggle_edges);visibility.addWidget(self.show_edges)
        self.version_mode=QComboBox();self.version_mode.addItems(['A+B','A','B']);self.version_mode.currentTextChanged.connect(self.refresh_legend)
        visibility.addWidget(_label('Widok:','muted'));visibility.addWidget(self.version_mode)
        self.dim_unchanged=QCheckBox('Przygaś bez zmian');self.dim_unchanged.setChecked(True);self.dim_unchanged.toggled.connect(self.refresh_legend);visibility.addWidget(self.dim_unchanged)
        visibility.addStretch();visibility.addWidget(_button('Inny podgląd…',self.toggle_advanced_view,'subtle'));v.addLayout(visibility)
        self.coverage_banner=_label('Wczytaj model A i B, aby rozpocząć.','muted');v.addWidget(self.coverage_banner)
        frame=_panel();frame.setMinimumHeight(300)
        fl=QVBoxLayout(frame);fl.setContentsMargins(8,8,8,8)
        self.vtk_host=QWidget();self.vtk_layout=QVBoxLayout(self.vtk_host);self.vtk_layout.setContentsMargins(0,0,0,0)
        self.viewer_hint=_label('◈  Wybierz model i kliknij „Załaduj model 3D”')
        self.viewer_hint.setAlignment(Qt.AlignCenter);self.vtk_layout.addWidget(self.viewer_hint)
        split=QSplitter()
        tree_panel=QWidget();tree_layout=QVBoxLayout(tree_panel);tree_layout.setContentsMargins(0,0,8,0)
        self.tree_search=QLineEdit();self.tree_search.setPlaceholderText('Szukaj części…');self.tree_search.textChanged.connect(self.filter_tree);tree_layout.addWidget(self.tree_search)
        self.parts_tree=QTreeWidget();self.parts_tree.setHeaderLabels(['CZĘŚCI / WYSTĄPIENIA']);self.parts_tree.setMinimumWidth(240);self.parts_tree.setUniformRowHeights(True);tree_layout.addWidget(self.parts_tree,1)
        self.parts_tree.itemChanged.connect(self.tree_visibility)
        self.parts_tree.itemClicked.connect(self.tree_select)
        self.change_list=QListWidget();self.change_list.itemClicked.connect(self.select_change)
        self.change_tabs=QTabWidget();self.change_tabs.addTab(self.make_change_panel(),'Zmiany');self.change_tabs.addTab(tree_panel,'Wszystkie części')
        split.addWidget(self.change_tabs);split.addWidget(self.vtk_host);split.setStretchFactor(1,1)
        self.inspector=_panel();self.inspector.setMinimumWidth(220);self.inspector.setMaximumWidth(285)
        detail=QVBoxLayout(self.inspector);detail.addWidget(_label('Wybrana zmiana','section'))
        self.inspector_text=_label('');self.inspector_text.setWordWrap(True);detail.addWidget(self.inspector_text)
        detail.addWidget(_button('Pokaż różnicę',self.detail_selected,'primary'))
        self.manual_button=_button('Wskaż parę A/B…',self.correct_pair);detail.addWidget(self.manual_button)
        detail.addWidget(_button('Zamknij szczegóły',self.inspector.hide,'subtle'));detail.addStretch()
        split.addWidget(self.inspector);self.inspector.hide();split.setSizes([255,850,250])
        fl.addWidget(split,1)
        v.addWidget(frame,1)
        self.viewer_message=_label('Podgląd tworzy uproszczoną siatkę całego modelu. Analiza B-Rep pozostaje dokładna.','muted')
        v.addWidget(self.viewer_message)

    def build_results(self):
        v=self.top('results','Wyniki porównania','Wybierz zmianę i otwórz kolorowy podgląd 3D')
        self.results_kpis=QHBoxLayout();self.results_numbers={}
        for key,name in STATUS_NAMES.items():
            card=_panel();l=QVBoxLayout(card);l.setContentsMargins(13,12,13,12)
            t=_label('—','kpi');t.setStyleSheet('color:'+self.settings['kolory'][key]);l.addWidget(t)
            caption=_label(name,'muted');caption.setWordWrap(True);l.addWidget(caption);self.results_numbers[key]=t
            self.results_kpis.addWidget(card)
        v.addLayout(self.results_kpis)
        line=QHBoxLayout();line.addWidget(_label('Szukaj:','muted'))
        self.filter_results=QLineEdit();self.filter_results.setPlaceholderText('Nazwa części, opis zmiany…');line.addWidget(self.filter_results,1)
        self.filter_results.textChanged.connect(self.apply_filter)
        self.only_changed=QCheckBox('Tylko zmiany');self.only_changed.toggled.connect(self.apply_filter)
        line.addWidget(self.only_changed)
        self.status_filter=QComboBox();self.status_filter.addItem('Wszystkie rodzaje','')
        for code,title in STATUS_NAMES.items():self.status_filter.addItem(title,code)
        self.status_filter.currentIndexChanged.connect(self.apply_filter);line.addWidget(self.status_filter)
        v.addLayout(line)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['Rodzaj','Nazwa A','Nazwa B','Przesunięcie [mm]','Uwagi'])
        self.table.setAlternatingRowColors(True);self.table.setSortingEnabled(True);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch)
        self.table.setColumnWidth(0,165);self.table.setColumnWidth(1,170);self.table.setColumnWidth(2,170);self.table.setColumnWidth(3,180)
        v.addWidget(self.table,1)
        self.result_detail=_label('Wybierz część, aby zobaczyć pełne dane. Dwuklik otwiera i przybliża ją w 3D.','muted')
        self.result_detail.setWordWrap(True);v.addWidget(self.result_detail)
        self.table.itemSelectionChanged.connect(self.show_result_detail)
        self.table.cellDoubleClicked.connect(self.show_selected_3d)
        btn=QHBoxLayout();btn.addWidget(_button('◈  Podgląd 3D',self.show_selected_3d,'primary'))
        btn.addWidget(_button('Raport HTML',lambda:self.open_result('RAPORT.html')))
        btn.addWidget(_button('Kolorowy STEP',lambda:self.open_result('POROWNANIE_KOLORY.step')))
        btn.addStretch();btn.addWidget(_button('Folder wyników',self.open_folder))
        btn.addWidget(_button('Eksport STEP / różnic…',self.export_result))
        btn.addWidget(_button('Otwórz analizę…',self.reopen_result))
        v.addLayout(btn)

    def build_mass(self):
        v=self.top('mass','Masa części','Obliczanie masy jednego modelu — bez porównywania dwóch plików')
        p=_panel();pl=QVBoxLayout(p);pl.setContentsMargins(22,20,22,20);pl.setSpacing(16)
        r,self.mass_file=self._file_line('PLIK MODELU STEP / STP');pl.addLayout(r)
        row=QHBoxLayout();row.addWidget(_label('Gęstość [kg/m³]','muted'))
        self.mass_density=QLineEdit('7850');self.mass_density.setMaximumWidth(170);row.addWidget(self.mass_density);row.addStretch();pl.addLayout(row)
        row=QHBoxLayout();self.mass_go=_button('◉  Oblicz masy',self.start_mass,'primary');row.addWidget(self.mass_go)
        self.mass_cancel=_button('Anuluj',self.cancel);self.mass_cancel.setEnabled(False);row.addWidget(self.mass_cancel)
        row.addWidget(_button('Raport HTML',lambda:self.open_result('RAPORT_MASY.html')));row.addWidget(_button('CSV do Excela',lambda:self.open_result('MASY_CZESCI.csv')));row.addStretch();pl.addLayout(row)
        v.addWidget(p)
        self.mass_progress=QProgressBar()
        self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
        self.mass_progress.setTextVisible(False)
        v.addWidget(self.mass_progress)
        self.mass_status=_label('Wybierz STEP i kliknij „Oblicz masy”.','muted')
        v.addWidget(self.mass_status)
        correction=QHBoxLayout()
        self.mass_edit=_button('Edytuj ilości',self.toggle_mass_edit,'subtle')
        self.mass_export=_button('Zapisz skorygowane CSV',self.export_corrected_mass,'subtle')
        self.mass_export.setEnabled(False)
        correction.addWidget(self.mass_edit);correction.addWidget(self.mass_export)
        correction.addStretch();v.addLayout(correction)
        self.mass_summary=_label('Wczytaj pojedynczy STEP, aby otrzymać masy i BOM.','muted');v.addWidget(self.mass_summary)
        self.mass_table=QTableWidget(0,5)
        self.mass_table.setHorizontalHeaderLabels(['Część','Ilość','Objętość [mm³]','Masa szt. [kg]','Masa łączna [kg]'])
        self.mass_table.setAlternatingRowColors(True);self.mass_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mass_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mass_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mass_editing=False
        self.mass_table.cellChanged.connect(self._mass_cell_changed)
        self.mass_table.cellDoubleClicked.connect(self.show_mass_part)
        self.mass_table.verticalHeader().setVisible(False)
        v.addWidget(self.mass_table,1)

    def build_settings(self):
        v=self.top('settings','Ustawienia','Motyw aplikacji, własne kolory zmian oraz eksportu STEP')
        p=_panel();pl=QVBoxLayout(p);pl.setContentsMargins(22,18,22,18)
        pl.addWidget(_label('Wygląd aplikacji','section'))
        row=QHBoxLayout();row.addWidget(_label('Motyw:','muted'))
        self.theme_select=QComboBox();self.theme_select.addItems(['ciemny','jasny']);self.theme_select.currentTextChanged.connect(self.set_theme)
        row.addWidget(self.theme_select);row.addStretch();pl.addLayout(row)
        pl.addSpacing(12);pl.addWidget(_label('Kolory porównania','section'))
        filter_panel=QHBoxLayout();filter_panel.addWidget(_label('Pokazuj wyniki:','muted'))
        self.category_checks={}
        for key in STATUS_NAMES:
            cb=QCheckBox(STATUS_NAMES[key]);cb.setChecked(self.settings.get('widoczne_statusy',{}).get(key,True))
            cb.toggled.connect(self.save_category_filters);self.category_checks[key]=cb;filter_panel.addWidget(cb)
        pl.addLayout(filter_panel)
        pl.addWidget(_label('Filtry ukrywają kategorie; pełna analiza nadal rozpoznaje przemieszczenia i zmiany geometrii.','muted'))
        self.color_buttons={};self.color_labels={} 
        grid=QGridLayout();grid.setHorizontalSpacing(12);grid.setVerticalSpacing(10)
        for idx,(status,name) in enumerate([(k,v) for k,v in STATUS_NAMES.items() if k!='RENAMED']):
            card=QFrame();card.setObjectName('colorcard')
            line=QHBoxLayout(card);line.setContentsMargins(12,8,12,8)
            swatch=QLabel('');swatch.setFixedSize(27,27);line.addWidget(swatch)
            labels=QVBoxLayout();labels.addWidget(_label(name))
            hex_label=_label('','muted');labels.addWidget(hex_label)
            line.addLayout(labels,1)
            btn=_button('Wybierz',lambda checked=False,k=status:self.change_color(k),'subtle')
            line.addWidget(btn)
            self.color_buttons[status]=swatch;self.color_labels[status]=hex_label
            grid.addWidget(card,idx//2,idx%2)
        pl.addLayout(grid)
        pl.addWidget(_button('Przywróć kolory domyślne',self.reset_colors,'subtle'))
        v.addWidget(p);v.addStretch()

    def navigate(self,key):
        self.stack.setCurrentWidget(self.pages[key]);self.current_page=key
        for k,b in self.nav.items():
            b.setIcon(menu_icon(dict((t[0],t[2]) for t in TABS)[k], '#F59E38' if k==key else ('#586477' if self.settings['motyw']=='jasny' else '#ACB5C9')));b.setProperty('active',str(k==key).lower());b.style().unpolish(b);b.style().polish(b)

    def set_theme(self,name,persist=True):
        self.settings['motyw']=name
        self.root.setStyleSheet(theme_qss(name=='jasny'))
        self.theme_select.blockSignals(True);self.theme_select.setCurrentText(name);self.theme_select.blockSignals(False)
        self.update_color_buttons()
        self.navigate(getattr(self,'current_page','start'))
        if persist:save_settings(self.settings)

    def toggle_theme(self):self.set_theme('jasny' if self.settings['motyw']=='ciemny' else 'ciemny')
    def update_color_buttons(self):
        for key,b in self.color_buttons.items():
            color=self.settings['kolory'].get(key,COLORS[key])
            b.setStyleSheet(f'background:{color};border:1px solid #808693;border-radius:8px;')
            self.color_labels[key].setText(color.upper())
    def change_color(self,key):
        color=QColorDialog.getColor(QColor(self.settings['kolory'].get(key,COLORS[key])),self,'Wybierz kolor')
        if color.isValid():
            self.settings['kolory'][key]=color.name().upper()
            self._sync_status_colors()
            self.update_color_buttons();save_settings(self.settings)
    def reset_colors(self):self.settings['kolory']=dict(COLORS);self._sync_status_colors();self.update_color_buttons();save_settings(self.settings)
    def show_about(self):
        QMessageBox.information(self,'O programie','DS Compare\nWersja 4.2\nAutor: Szymczyk Damian\n'
                'Analiza geometrii: Open CASCADE\nPodgląd 3D: VTK\nInterfejs: Qt')
    def swap_models(self):a=self.file_a.text();self.file_a.setText(self.file_b.text());self.file_b.setText(a)

    def _numeric(self,text,minimum,maximum,label):
        try:n=float(text.replace(',','.'))
        except ValueError:raise ValueError(f'{label}: podaj liczbę')
        if not minimum<n<=maximum:raise ValueError(f'{label}: wartość poza zakresem')
        return n

    def start_compare(self):
        try:
            a,b=Path(self.file_a.text()),Path(self.file_b.text())
            if not a.is_file() or not b.is_file():raise ValueError('Wybierz dwa istniejące pliki STEP')
            tol=self._numeric(self.tolerance.text(),0,1,'Tolerancja')
            rho=self._numeric(self.density.text(),0,25000,'Gęstość')
            if a.suffix.lower() not in ('.step','.stp') or b.suffix.lower() not in ('.step','.stp'):raise ValueError('Wybierz pliki STEP/STP')
            if a.resolve()==b.resolve():raise ValueError('Wybierz dwie różne wersje modelu')
            if not self.file_out.text().strip():raise ValueError('Wybierz katalog wyników')
            folder=Path(self.file_out.text())/datetime.now().strftime('Porownanie_%Y%m%d_%H%M%S_%f')
            folder.mkdir(parents=True,exist_ok=False)
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Dane wejściowe',str(exc));return
        colors={k:[int(v[i:i+2],16)/255 for i in (1,3,5)] for k,v in self.settings['kolory'].items()}
        args=['--worker','compare','--a',str(a),'--b',str(b),'--output',str(folder),
              '--direct-scene','--tolerance',str(tol),'--density',str(rho),'--schema',self.schema.currentText(),'--palette',json.dumps(colors)]
        if self.write_step.isChecked():args.append('--generate-step')
        if self.make_diff.isChecked():args.append('--diff-step')
        if self.align_models.isChecked():args.append('--align')
        self.settings['step_schema']=self.schema.currentText();save_settings(self.settings)
        self.file_a.setText(str(a));self.file_b.setText(str(b))
        self.launch_worker('compare',args,folder)

    def start_mass(self):
        try:
            step=Path(self.mass_file.text());rho=self._numeric(self.mass_density.text(),0,25000,'Gęstość')
            if not step.is_file():raise ValueError('Wskaż istniejący model STEP')
        except ValueError as exc:QMessageBox.warning(self,'Masa części',str(exc));return
        folder=Path(self.file_out.text())/'Masa_czesci'
        self.launch_worker('mass',['--worker','mass','--input',str(step),'--output',str(folder),'--density',str(rho)],folder)

    def choose_viewer_file(self):
        start=self.viewer_custom_path.text().strip() or str(Path.home())
        selected=QFileDialog.getOpenFileName(self,'Wybierz dowolny STEP',start,'STEP (*.step *.stp)')[0]
        if selected:
            self.viewer_custom_path.setText(selected)
            self.viewer_model.setCurrentIndex(0)
            self.settings['ostatni_podglad']=selected
            save_settings(self.settings)

    def start_mesh(self):
        idx=self.viewer_model.currentIndex()
        if idx==1 and (self.result_dir/'SCENA_WYNIK.npz').exists():
            self.render_vtk(self.result_dir/'SCENA_WYNIK.npz');return
        if idx==1 and self.process and self.process.state()!=QProcess.NotRunning:
            self.viewer_message.setText('Wynik jest gotowy; trwa przygotowanie siatki. Poczekaj na zakończenie.');return
        if idx==0:
            text=self.viewer_custom_path.text().strip()
            if not text:
                self.choose_viewer_file()
                text=self.viewer_custom_path.text().strip()
                if not text:return
            step=Path(text)
        elif idx==1:step=self.result_dir/'POROWNANIE_KOLORY.step'
        elif idx==2:step=Path(self.file_a.text())
        elif idx==3:step=Path(self.file_b.text())
        else:step=self.result_dir/'ROZNICE_BREP.step'
        if not step.is_file():QMessageBox.warning(self,'Podgląd','Brak pliku STEP. Wybierz model lub wykonaj porównanie.');return
        import hashlib
        identifier=hashlib.sha1(('v40'+str(step.resolve())+str(step.stat().st_mtime_ns)+self.viewer_quality.currentText()).encode()).hexdigest()[:12]
        folder=_settings_path().parent/'Cache_3D'/identifier
        self.loaded_mesh_source=step
        cached=folder/'SCENA_3D.npz'
        if cached.exists():self.render_vtk(cached);return
        args=['--worker','mesh','--input',str(step),'--output',str(folder),'--quality',self.viewer_quality.currentText()]
        self.launch_worker('mesh',args,folder)

    def launch_worker(self,kind,args,folder):
        if self.process and self.process.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Trwa analiza','Najpierw zakończ lub anuluj aktualne zadanie.');return
        folder.mkdir(parents=True,exist_ok=True)
        self.worker_kind=kind;self.worker_dir=folder;self.worker_position=0;self.cancelled=False
        self.status.setText({'compare':'Porównywanie B-Rep…','mass':'Obliczanie mas…','mesh':'Tworzenie podglądu 3D…'}.get(kind,kind))
        if kind=='compare':self.progress.setRange(0,0)
        if kind=='mesh':
            self.viewer_progress.show()
            self.viewer_progress.setRange(0,0)
        self.btn_compare.setEnabled(False);self.quick_compare.setEnabled(False);self.mass_go.setEnabled(False);self.mesh_button.setEnabled(False)
        self.btn_cancel.setEnabled(True);self.mass_cancel.setEnabled(True)
        self.progress.setTextVisible(False)
        if kind=='mass':
            self.mass_progress.setRange(0,0)
            self.mass_status.setText('Wczytywanie geometrii STEP…')
        if kind=='compare':self.log.clear()
        self.early_result_loaded=False
        self.process=QProcess(self)
        self.process.finished.connect(self.worker_finished)
        self.process.errorOccurred.connect(self.worker_error)
        if getattr(sys,'frozen',False):
            self.process.start(sys.executable,args)
        else:
            self.process.start(sys.executable,[str(Path(__file__).resolve().parents[1]/'DSCompareV3.py'),*args])
        if not hasattr(self,'worker_timer'):
            self.worker_timer=QTimer(self);self.worker_timer.timeout.connect(self.read_progress)
        self.worker_timer.start(250)

    def read_progress(self):
        if not self.worker_dir:return
        path=self.worker_dir/'_POSTEP_V37.jsonl'
        if not path.exists():return
        try:
            with path.open('r',encoding='utf-8') as stream:
                stream.seek(self.worker_position)
                lines=stream.readlines();self.worker_position=stream.tell()
            for line in lines:
                try:msg=json.loads(line)['tekst']
                except (ValueError,KeyError):continue
                if self.worker_kind=='compare':self.log.append(msg)
                self.status.setText(msg)
                if self.worker_kind=='mesh':self.viewer_message.setText(msg)
                if self.worker_kind=='mass':self.mass_status.setText(msg)
            if self.worker_kind=='compare' and not self.early_result_loaded and (self.worker_dir/'PODSUMOWANIE.json').exists():
                self.result_dir=self.worker_dir;self.load_summary();self.navigate('results');self.early_result_loaded=True
        except (OSError,UnicodeError,ValueError):pass

    def worker_finished(self,code,status):
        self.read_progress();self.worker_timer.stop()
        self.viewer_progress.hide()
        self.progress.setRange(0,100);self.progress.setValue(100 if code==0 else 0)
        self.progress.setFormat('Ukończono' if code==0 else 'Błąd')
        self.mass_progress.setRange(0,100)
        self.mass_progress.setValue(100 if code==0 else 0)
        self.mass_progress.setFormat('Ukończono' if code==0 else 'Błąd')
        self.mass_cancel.setEnabled(False)
        if self.worker_kind=='mass':
            self.mass_status.setText('Ukończono' if code==0 else 'Błąd obliczania mas')
        for button in (self.btn_compare,self.quick_compare,self.mass_go,self.mesh_button):button.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if self.cancelled:
            self.status.setText('Anulowano — poprzedni wynik pozostał dostępny')
            self.viewer_message.setText('Anulowano przygotowanie podglądu')
            return
        result=self.worker_dir/'_WYNIK_V37.json'
        try:data=json.loads(result.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            QMessageBox.critical(self,'Błąd','Proces zakończył się bez raportu. Sprawdź dziennik.')
            return
        if not data.get('ok'):
            QMessageBox.critical(self,'Błąd analizy',data.get('error','Nieznany błąd')[-1800:]);return
        self.status.setText('Zakończono pomyślnie')
        if self.worker_kind=='compare':
            self.result_dir=Path(data['folder']);self.settings['ostatni_wynik']=str(self.result_dir);save_settings(self.settings);self.load_summary();self.navigate('results')
            scene=self.result_dir/'SCENA_WYNIK.npz'
            if scene.exists():self.render_vtk(scene)
            scene_warning=self.result_dir/'UWAGI_SCENA.txt'
            if scene_warning.exists():QMessageBox.warning(self,'Podgląd',scene_warning.read_text(encoding='utf-8'))
            if data.get('alignment',{}).get('warning'):
                self.status.setText('Ukończono bez wyrównania — sprawdź ostrzeżenie')
                QMessageBox.warning(self,'Wyrównanie modeli',data['alignment']['warning'])
            if data.get('blad_step'):
                QMessageBox.warning(self,'Ostrzeżenie STEP',str(data['blad_step']))
        elif self.worker_kind=='detail':
            scene=Path(data['folder'])/'SCENA_WYNIK.npz'
            if scene.exists():self.render_vtk(scene)
            else:QMessageBox.information(self,'Szczegóły','Nie znaleziono dodatnich objętości różnic w wybranej parze.')
        elif self.worker_kind=='mass':
            self.mass_result_dir=Path(data['folder'])
            s=data['podsumowanie'];self.mass_summary.setText(
                f"Brył: {s['liczba_bryl']}   •   Pozycji: {s['liczba_pozycji']}   •   Masa łączna: {s['masa_calosci_kg']:.3f} kg".replace('.',','))
            self.fill_mass_table(self.worker_dir/'MASY_CZESCI.csv')
            if (self.mass_result_dir/'UWAGI_SCENA.txt').exists():
                self.mass_status.setText('Raport masy gotowy; podgląd niedostępny — zobacz UWAGI_SCENA.txt')
        else:self.render_vtk(self.worker_dir/'SCENA_3D.npz')

    def cancel(self):
        if self.process and self.process.state()!=QProcess.NotRunning:
            self.cancelled=True
            self.process.kill();self.status.setText('Przerwano — proces obliczeniowy zatrzymany')
            self.mass_status.setText('Anulowano analizę masy')

    def load_summary(self):
        summary=self.result_dir/'PODSUMOWANIE.json'
        if not summary.is_file():return
        try:content=json.loads(summary.read_text(encoding='utf-8'));statuses=content['statuses']
        except (OSError,ValueError,KeyError):return
        for key,value in [('SAME',statuses.get('SAME',0)+statuses.get('RENAMED',0)),
                          ('CHANGED',sum(statuses.get(x,0) for x in ('CHANGED','MOVED','ADDED','UNCERTAIN'))),
                          ('REMOVED',statuses.get('REMOVED',0))]:
            getattr(self,'kpi_'+key).setText(str(value))
        for key,lbl in self.results_numbers.items():
            value=statuses.get(key,0)
            lbl.setText(str(value))
        self.result_records=content.get('records',[])
        self.result_detail.setText(f"Sprawdzono A: {content.get('solids_A',0)}/{content.get('solids_A',0)} · B: {content.get('solids_B',0)}/{content.get('solids_B',0)} · Pozycji: {len(self.result_records)}")
        self.result_palette=content.get('colors_hex',self.settings['kolory'])
        path=self.result_dir/'ZMIANY.csv'
        if not path.exists():return
        with path.open('r',encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream,delimiter=';'))
        self.table.setSortingEnabled(False);self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            record=self.result_records[i] if i<len(self.result_records) else {}
            vals=[STATUS_NAMES.get(record.get('status'),row.get('Rodzaj zmiany','')),row.get('Nazwa A',''),row.get('Nazwa B',''),
                  row.get('Przesunięcie środka [mm]',''),row.get('Uwagi','')]
            for k,val in enumerate(vals):
                if val.startswith('="') and val.endswith('"'):val=val[2:-1]
                item=QTableWidgetItem(val)
                item.setData(Qt.UserRole,i)
                item.setToolTip(val)
                if k==0:
                    c='#58C8B1' if 'Bez zmian' in val else '#F6AF67' if 'Usuni' in val else '#C2B4FC'
                    record=self.result_records[i] if i<len(self.result_records) else {}
                    item.setForeground(QColor(self.result_palette.get(record.get('status'),c)))
                self.table.setItem(i,k,item)
        self.table.setSortingEnabled(True);self.apply_filter();self.populate_changes(content,rows)

    def save_category_filters(self,*_):
        self.settings['widoczne_statusy']={k:cb.isChecked() for k,cb in self.category_checks.items()}
        save_settings(self.settings);self.apply_filter();self.filter_changes()
        for k,cb in self.legend_filters.items():
            cb.setChecked(self.settings['widoczne_statusy'].get(k,True))
        self.refresh_legend()

    def apply_filter(self,*_):
        target=self.filter_results.text().casefold().strip()
        for i in range(self.table.rowCount()):
            values=[self.table.item(i,j).text() if self.table.item(i,j) else '' for j in range(self.table.columnCount())]
            show=(not target or any(target in v.casefold() for v in values)) and (
                not self.only_changed.isChecked() or 'Bez zmian' not in values[0])
            idx=self.table.item(i,0).data(Qt.UserRole)
            records=getattr(self,'result_records',[])
            status=records[idx]['status'] if idx is not None and idx<len(records) else ''
            if status:
                show=(not target or any(target in v.casefold() for v in values)) and (not self.only_changed.isChecked() or status!='SAME')
                show=show and (not self.status_filter.currentData() or self.status_filter.currentData()==status)
            show=show and self.settings.get('widoczne_statusy',{}).get(status,True)
            self.table.setRowHidden(i,not show)

    def fill_mass_table(self,path):
        with path.open('r',encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream,delimiter=';'))
        self.mass_table.blockSignals(True)
        self.mass_table.setRowCount(len(rows))
        keys=['Nazwa części','Ilość','Objętość jednej sztuki [mm³]','Masa jednej sztuki [kg]','Masa łączna [kg]']
        for i,row in enumerate(rows):
            for j,k in enumerate(keys):
                item=QTableWidgetItem(row.get(k,''))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if j:item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                self.mass_table.setItem(i,j,item)
        self.mass_table.blockSignals(False)

    def toggle_mass_edit(self):
        self.mass_editing=not self.mass_editing
        self.mass_table.setEditTriggers(QAbstractItemView.DoubleClicked if self.mass_editing else QAbstractItemView.NoEditTriggers)
        self.mass_edit.setText('Zakończ edycję ilości' if self.mass_editing else 'Edytuj ilości')
        self.mass_export.setEnabled(self.mass_editing)
        for row in range(self.mass_table.rowCount()):
            for col in range(self.mass_table.columnCount()):
                cell=self.mass_table.item(row,col)
                if cell:
                    flags=cell.flags()
                    cell.setFlags(flags | Qt.ItemIsEditable if col==1 and self.mass_editing else flags & ~Qt.ItemIsEditable)

    def _mass_cell_changed(self,row,col):
        if col!=1 or not self.mass_editing:return
        try:
            count=int(self.mass_table.item(row,1).text().strip())
            if not 0<=count<=1000000:raise ValueError()
            unit=float(self.mass_table.item(row,3).text().replace(',','.'))
        except (ValueError,AttributeError):
            self.mass_status.setText('Nieprawidłowa ilość — wpisz liczbę od 0 do 1 000 000')
            return
        self.mass_table.blockSignals(True)
        self.mass_table.item(row,4).setText(f'{unit*count:.5f}'.replace('.',','))
        self.mass_table.blockSignals(False)
        total=0.
        for row in range(self.mass_table.rowCount()):
            try:total+=float(self.mass_table.item(row,4).text().replace(',','.'))
            except (ValueError,AttributeError):pass
        self.mass_summary.setText(f'Korekta ilości (bez zmian STEP) • Masa łączna: {total:.3f} kg'.replace('.',','))

    def export_corrected_mass(self):
        path,_=QFileDialog.getSaveFileName(self,'Zapisz skorygowane zestawienie',
                str(self.worker_dir/'MASY_CZESCI_SKORYGOWANE.csv'),'CSV (*.csv)')
        if not path:return
        import csv
        with open(path,'w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f,delimiter=';')
            writer.writerow([self.mass_table.horizontalHeaderItem(i).text() for i in range(self.mass_table.columnCount())])
            for row in range(self.mass_table.rowCount()):
                writer.writerow([self.mass_table.item(row,col).text() for col in range(self.mass_table.columnCount())])
        self.mass_status.setText('Zapisano skorygowany CSV — oryginalny BOM pozostawiono bez zmian')

    def toggle_advanced_view(self):
        show=not self.advanced_view.isVisible();self.advanced_view.setVisible(show)
        self.custom_source_row.setVisible(show and self.viewer_model.currentIndex()==0)

    def make_change_panel(self):
        panel=QWidget();layout=QVBoxLayout(panel);layout.setContentsMargins(0,8,8,0)
        self.change_search=QLineEdit();self.change_search.setPlaceholderText('Szukaj zmiany…');self.change_search.textChanged.connect(self.filter_changes)
        layout.addWidget(self.change_search);layout.addWidget(self.change_list,1)
        return panel

    def filter_changes(self,*_):
        query=self.change_search.text().casefold().strip()
        for n in range(self.change_list.count()):
            item=self.change_list.item(n);rid=item.data(Qt.UserRole)
            status=self.result_records[rid]['status']
            cb=self.legend_filters.get('SAME' if status=='RENAMED' else status)
            item.setHidden((query not in item.text().casefold()) or not self.settings.get('widoczne_statusy',{}).get(status,True) or (cb is not None and not cb.isChecked()))

    def populate_changes(self,content,rows):
        self.change_list.clear();self.change_names={};self.change_pair_names={}
        for i,record in enumerate(content.get('records',[])):
            row=rows[i] if i<len(rows) else {}
            name=row.get('Nazwa B') or row.get('Nazwa A') or f'Część {i+1}'
            self.change_names[i]=name
            self.change_pair_names[i]={'A':row.get('Nazwa A',''),'B':row.get('Nazwa B','')}
            if record['status']=='SAME':continue
            item=QListWidgetItem(STATUS_NAMES.get(record['status'],record['status'])+' · '+name)
            item.setData(Qt.UserRole,i);item.setToolTip(record.get('note',''))
            text_color=QColor(self.result_palette.get(record['status'],'#ACB5C9'))
            if record['status']=='CHANGED' and self.settings.get('motyw')!='jasny':text_color=text_color.lighter(150)
            item.setForeground(text_color)
            self.change_list.addItem(item)
        self.change_tabs.setTabText(0,f'Zmiany ({self.change_list.count()})')
        records=content.get('records',[])
        ca=len({r['a_index'] for r in records if r['a_index'] is not None});cb=len({r['b_index'] for r in records if r['b_index'] is not None})
        label=f"Analiza A: {ca}/{content.get('solids_A',0)} · B: {cb}/{content.get('solids_B',0)}"
        audit=self.result_dir/'SCENA_DIAGNOSTYKA.json'
        if audit.exists():
            data=json.loads(audit.read_text(encoding='utf-8'))
            label+=f" · Podgląd: {data['rendered_records']}/{data['expected_records']} · Błędy siatki: {len(data['errors'])}"
        else:label+=' · Podgląd jeszcze niegotowy'
        self.coverage_banner.setText(label);self.filter_changes()

    def select_change(self,item):
        self.pending_record_id=item.data(Qt.UserRole)
        self.viewer_model.setCurrentIndex(1);self.start_mesh()

    def update_inspector(self,body_index):
        from .scene42 import metadata
        name=self.body_actors[body_index][0];status,rid=metadata(name)
        if not getattr(self,'scene_is_result',False) or rid is None:return
        records=getattr(self,'result_records',[])
        if rid>=len(records):return
        record=records[rid]
        title=getattr(self,'change_names',{}).get(rid,name)
        self.inspector_text.setText(title+'\n\n'+STATUS_NAMES.get(status,status)+'\n\n'+record.get('note','')+'\n\nPodstawa: '+record.get('confidence',''))
        self.manual_button.setEnabled(status in ('UNCERTAIN','CHANGED','ADDED','REMOVED') or record.get('confidence')=='Para użytkownika')
        self.inspector.show()

    def correct_pair(self):
        if self.process and self.process.state()!=QProcess.NotRunning:return
        data=json.loads((self.result_dir/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        if not data.get('source_fingerprints'):
            QMessageBox.information(self,'Pary','Najpierw wykonaj analizę w wersji 4.4.');return
        records=data['records'];choices={'A':{},'B':{}}
        for rid,r in enumerate(records):
            if r['status'] not in ('UNCERTAIN','CHANGED','ADDED','REMOVED') and r.get('confidence')!='Para użytkownika':continue
            for side,key in [('A','a_index'),('B','b_index')]:
                if r[key] is not None:choices[side][f"{side} #{r[key]+1} · {self.change_pair_names.get(rid,{}).get(side,'Część')}"]=r[key]
        if not choices['A'] or not choices['B']:
            QMessageBox.information(self,'Pary','Brak części A i B wymagających dopasowania.');return
        first,ok=QInputDialog.getItem(self,'Ręczna para','Wybierz część A:',list(choices['A']),0,False)
        if not ok:return
        second,ok=QInputDialog.getItem(self,'Ręczna para','Wybierz odpowiadającą część B:',list(choices['B']),0,False)
        if not ok:return
        i=choices['A'][first];j=choices['B'][second]
        pairs=[p for p in data.get('manual_pairs',[]) if p[0]!=i and p[1]!=j]+[[i,j]]
        folder=self.result_dir.parent/datetime.now().strftime('Korekta_%Y%m%d_%H%M%S_%f');folder.mkdir()
        request=folder/'PARY_UZYTKOWNIKA.json';request.write_text(json.dumps({'pairs':pairs,'fingerprints':data['source_fingerprints']},indent=2),encoding='utf-8')
        args=['--worker','compare','--a',data['source_A'],'--b',data['source_B'],'--output',str(folder),'--direct-scene','--manual-review',str(request),'--tolerance',str(data.get('tolerance_mm',.01)),'--density',str(data.get('density_kg_m3',7850))]
        palette={k:[int(v[n:n+2],16)/255 for n in (1,3,5)] for k,v in data.get('colors_hex',{}).items()}
        args+=['--palette',json.dumps(palette)]
        if data.get('alignment',{}).get('requested'):args.append('--align')
        self.launch_worker('compare',args,folder)

    def filter_tree(self,*_):
        query=self.tree_search.text().casefold().strip()
        for i in range(self.parts_tree.topLevelItemCount()):
            parent=self.parts_tree.topLevelItem(i);found=False
            for j in range(parent.childCount()):
                item=parent.child(j);matches=not query or query in item.text(0).casefold()
                item.setHidden(not matches);found|=matches
            parent.setHidden(not found)
            if query:parent.setExpanded(True)

    def toggle_edges(self,checked):
        for _,actor in getattr(self,'body_actors',[]):actor.GetProperty().SetEdgeVisibility(checked)
        if self.viewer_ready:self.vtk_widget.GetRenderWindow().Render()

    def fit_model(self):
        if self.viewer_ready:
            self.renderer.ResetCamera()
            self.vtk_widget.GetRenderWindow().Render()

    def refresh_legend(self,*_):
        if hasattr(self,'change_search'):self.filter_changes()
        if not self.viewer_ready:return
        count=0
        from .scene42 import metadata
        for i,(name,actor) in enumerate(self.body_actors):
            status,_=metadata(name)
            raw_status=status;status='SAME' if status=='RENAMED' else status
            cb=self.legend_filters.get(status)
            visible=(not cb or cb.isChecked()) and self.settings.get('widoczne_statusy',{}).get(raw_status,True) and i not in getattr(self,'hidden_bodies',set())
            from .view_state import visible_version,opacity
            part_role='A' if name.endswith('[A]') else 'B'
            mode=self.version_mode.currentText() if getattr(self,'scene_is_result',False) else 'A+B'
            if getattr(self,'scene_is_result',False):visible=visible and visible_version(raw_status,part_role,mode)
            actor.GetProperty().SetOpacity(opacity(raw_status,part_role,mode,self.dim_unchanged.isChecked()))
            role=name.endswith('[A]')
            if mode=='A+B' and role and status!='REMOVED' and not self.old_visible.isChecked():visible=False
            actor.SetVisibility(visible);count+=int(visible)
        self.viewer_message.setText(f'Widoczne bryły: {count}/{len(self.body_actors)} · '+getattr(self,'scene_description',''))
        self.vtk_widget.GetRenderWindow().Render()

    def set_visible_indices(self,indices):
        indices=set(indices)
        self.hidden_bodies=set(range(len(self.body_actors)))-indices
        self.parts_tree.blockSignals(True)
        for i,item in enumerate(self.body_items):item.setCheckState(0,Qt.Checked if i in indices else Qt.Unchecked)
        self.parts_tree.blockSignals(False);self.refresh_legend()

    def show_all_parts(self):
        if not self.viewer_ready:return
        for cb in self.category_checks.values():cb.setChecked(True)
        for cb in self.legend_filters.values():cb.setChecked(True)
        self.old_visible.setChecked(True)
        self.set_visible_indices(range(len(self.body_actors)));self.fit_model()

    def tree_visibility(self,item,column):
        index=item.data(0,Qt.UserRole)
        if index is None:return
        if item.checkState(0)==Qt.Checked:self.hidden_bodies.discard(index)
        else:self.hidden_bodies.add(index)
        self.refresh_legend()

    def tree_select(self,item,column=0):
        index=item.data(0,Qt.UserRole)
        if index is None:return
        from .scene42 import metadata
        self.active_body=index;self.update_inspector(index)
        rid=metadata(self.body_actors[index][0])[1]
        if getattr(self,'scene_is_result',False):
            for n in range(self.change_list.count()):
                if self.change_list.item(n).data(Qt.UserRole)==rid:self.change_list.setCurrentRow(n);break
        related=[i for i,(name,_) in enumerate(self.body_actors) if i==index or (rid is not None and metadata(name)[1]==rid)]
        self.parts_tree.blockSignals(True)
        for i,(_,actor) in enumerate(self.body_actors):
            selected=i in related
            actor.GetProperty().SetEdgeVisibility(selected or self.show_edges.isChecked())
            actor.GetProperty().SetEdgeColor(*((1.,.75,.2) if selected else (.15,.20,.26)))
            if selected:self.hidden_bodies.discard(i);self.body_items[i].setCheckState(0,Qt.Checked)
        self.parts_tree.blockSignals(False);self.refresh_legend()
        bounds=[self.body_actors[i][1].GetBounds() for i in related if self.body_actors[i][1].GetVisibility()]
        if bounds:
            combined=[(min if k%2==0 else max)(b[k] for b in bounds) for k in range(6)]
            self.renderer.ResetCamera(combined);self.renderer.GetActiveCamera().Zoom(.8)
        self.vtk_widget.GetRenderWindow().Render()

    def isolate_part(self):
        idx=getattr(self,'active_body',None)
        if idx is None:return
        from .scene42 import metadata
        rid=metadata(self.body_actors[idx][0])[1]
        self.set_visible_indices(i for i in range(len(self.body_actors)) if i==idx or (rid is not None and metadata(self.body_actors[i][0])[1]==rid))

    def next_change(self,direction):
        from .scene42 import metadata
        candidates=[];seen=set()
        allowed={self.change_list.item(n).data(Qt.UserRole) for n in range(self.change_list.count()) if not self.change_list.item(n).isHidden()}
        for i,(name,_) in enumerate(getattr(self,'body_actors',[])):
            status,rid=metadata(name)
            if getattr(self,'scene_is_result',False) and rid not in allowed:continue
            if status and status!='SAME' and rid not in seen and self.settings.get('widoczne_statusy',{}).get(status,True) and (not self.legend_filters.get('SAME' if status=='RENAMED' else status) or self.legend_filters['SAME' if status=='RENAMED' else status].isChecked()):
                seen.add(rid);candidates.append(i)
        if not candidates:return
        current=getattr(self,'active_body',None)
        pos=candidates.index(current) if current in candidates else (-1 if direction>0 else 0)
        idx=candidates[(pos+direction)%len(candidates)]
        self.parts_tree.setCurrentItem(self.body_items[idx]);self.tree_select(self.body_items[idx])

    def detail_selected(self):
        from .scene42 import metadata
        body=getattr(self,'active_body',None)
        if body is None:return
        if not getattr(self,'scene_is_result',False):
            QMessageBox.information(self,'Szczegóły','Szczegóły są dostępne dla głównego wyniku porównania.');return
        status,index=metadata(self.body_actors[body][0])
        if index is None or status not in ('CHANGED','UNCERTAIN','MOVED'):
            QMessageBox.information(self,'Szczegóły','Wybierz zmienioną lub niepewną parę z głównego wyniku.');return
        out=self.result_dir/f'Szczegoly_R{index:06d}'
        scene=out/'SCENA_WYNIK.npz'
        if scene.exists():self.render_vtk(scene);return
        summary=json.loads((self.result_dir/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        self.launch_worker('detail',['--worker','detail','--input',str(self.result_dir),'--record',str(index),
            '--output',str(out),'--tolerance',str(summary.get('tolerance_mm',0.01))],out)

    def show_mass_part(self,row,column=0):
        if self.mass_editing:return
        folder=getattr(self,'mass_result_dir',None)
        if not folder:return
        mapping=json.loads((folder/'MASA_MAPA.json').read_text(encoding='utf-8'))
        self.pending_record_id=mapping[row][0]
        self.render_vtk(folder/'SCENA_WYNIK.npz')
        from .scene42 import metadata
        self.set_visible_indices(i for i in range(len(self.body_actors)) if metadata(self.body_actors[i][0])[1] in mapping[row])
        self.fit_model()

    def reopen_result(self):
        folder=QFileDialog.getExistingDirectory(self,'Otwórz folder analizy',str(self.result_dir))
        if not folder:return
        if not (Path(folder)/'PODSUMOWANIE.json').is_file():
            QMessageBox.warning(self,'Analiza','Brak PODSUMOWANIE.json w wybranym folderze.');return
        self.result_dir=Path(folder);self.load_summary();self.navigate('results')

    def export_result(self):
        try:
            data=json.loads((self.result_dir/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
            a,b=data['source_A'],data['source_B']
            if not Path(a).is_file() or not Path(b).is_file():raise ValueError('Brakuje oryginalnych modeli A/B.')
        except (OSError,ValueError,KeyError) as exc:
            QMessageBox.warning(self,'Eksport',str(exc));return
        self.file_a.setText(a);self.file_b.setText(b)
        self.tolerance.setText(str(data.get('tolerance_mm',0.01)))
        self.density.setText(str(data.get('density_kg_m3',7850)))
        self.align_models.setChecked(data.get('alignment',{}).get('requested',False))
        self.write_step.setChecked(True);self.make_diff.setChecked(True)
        self.navigate('compare')
        self.status.setText('Eksport wymaga ponownego odczytu A/B. Kliknij Rozpocznij porównanie; powstanie osobny folder.')

    def worker_error(self,error):
        self.log.append('Proces: '+str(error))
        if error==QProcess.FailedToStart:
            if hasattr(self,'worker_timer'):self.worker_timer.stop()
            self.viewer_progress.hide()
            for btn in (self.btn_compare,self.quick_compare,self.mass_go,self.mesh_button):btn.setEnabled(True)
            self.btn_cancel.setEnabled(False);self.mass_cancel.setEnabled(False)
            self.progress.setRange(0,100);self.mass_progress.setRange(0,100)
            QMessageBox.critical(self,'Uruchomienie analizy',self.process.errorString())

    def selected_record_id(self):
        row=self.table.currentRow()
        item=self.table.item(row,0) if row>=0 else None
        return item.data(Qt.UserRole) if item else None

    def show_result_detail(self):
        idx=self.selected_record_id()
        if idx is None or idx>=len(getattr(self,'result_records',[])):return
        rec=self.result_records[idx]
        d=[rec.get(k) for k in ('delta_x','delta_y','delta_z')]
        delta=' / '.join('—' if x is None else f'{x:.3f}' for x in d)
        angle=rec.get('rotation_deg');angle='—' if angle is None else f'{angle:.3f}°'
        self.result_detail.setText(f"{rec.get('note','')}\nΔX / ΔY / ΔZ: {delta} mm · Obrót dopasowania: {angle} · {rec.get('confidence','')}")

    def show_selected_3d(self,*_):
        self.pending_record_id=self.selected_record_id()
        self.viewer_model.setCurrentIndex(1)
        self.navigate('viewer');self.start_mesh()

    def focus_selected_actor(self):
        idx=getattr(self,'pending_record_id',None)
        if idx is None:return
        token=f'[R{idx:06d}]'
        from .scene42 import metadata
        for i,(name,actor) in enumerate(getattr(self,'body_actors',[])):
            if token in name:
                status,_=metadata(name)
                if status in self.category_checks:self.category_checks[status].setChecked(True)
                key='SAME' if status=='RENAMED' else status
                if key in self.legend_filters:self.legend_filters[key].setChecked(True)
                self.parts_tree.setCurrentItem(self.body_items[i]);self.tree_select(self.body_items[i]);break
        self.pending_record_id=None

    def open_result(self,name):
        path=self.result_dir/name
        if not path.exists() and name in ('RAPORT_MASY.html','MASY_CZESCI.csv'):
            path=Path(self.file_out.text())/'Masa_czesci'/name
        if not path.exists():QMessageBox.warning(self,'Nie znaleziono pliku',str(path));return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def open_folder(self):
        folder=(Path(self.worker_dir) if self.worker_kind=='compare' and self.process
                and self.process.state()!=QProcess.NotRunning
                else self.result_dir)
        try:folder.mkdir(parents=True,exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self,'Folder wyników',str(exc));return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            QMessageBox.warning(self,'Folder wyników','Nie można otworzyć folderu: '+str(folder))

    def render_vtk(self,path):
        path=Path(path)
        if path.name=='SCENA_WYNIK.npz' and path.parent==self.result_dir:self.viewer_model.setCurrentIndex(1)
        if not path.is_file():
            self.viewer_message.setText('Podgląd niedostępny — sprawdź kompletność analizy.');return
        if getattr(self,'active_scene',None)==(str(path.resolve()),path.stat().st_mtime_ns):
            self.navigate('viewer');self.focus_selected_actor();return
        try:
            import os
            os.environ.setdefault('QT_API','pyside6')
            import numpy as np
            import vtkmodules.vtkRenderingOpenGL2
            import vtkmodules.vtkInteractionStyle
            from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
            from vtkmodules.vtkRenderingCore import vtkRenderer,vtkPolyDataMapper,vtkActor
            from vtkmodules.vtkCommonDataModel import vtkPolyData,vtkCellArray
            from vtkmodules.vtkCommonCore import vtkPoints
            from vtkmodules.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray
            arr=np.load(path,allow_pickle=False)
            vertex=arr['vertices'];offset=arr['offsets'];colors=arr['colors']
            if not self.viewer_ready:
                self.viewer_hint.hide()
                self.vtk_widget=QVTKRenderWindowInteractor(self.vtk_host)
                self.vtk_layout.addWidget(self.vtk_widget,1)
                self.renderer=vtkRenderer();self.renderer.SetBackground(0.73,0.78,0.84);self.renderer.SetBackground2(0.93,0.95,0.97);self.renderer.GradientBackgroundOn()
                self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
                self.interactor=self.vtk_widget.GetRenderWindow().GetInteractor()
                self.viewer_ready=True
            self.renderer.RemoveAllViewProps()
            self.viewer_actors={}
            self.body_actors=[];self.hidden_bodies=set();self.body_items=[];self.active_body=None
            self.parts_tree.blockSignals(True);self.parts_tree.clear();groups={}
            from .scene42 import metadata
            self.scene_description='Wynik porównania' if Path(path).parent==self.result_dir else 'Podgląd geometrii'
            self.inspector.hide()
            audit=Path(path).parent/'SCENA_DIAGNOSTYKA.json'
            if audit.exists():
                info=json.loads(audit.read_text(encoding='utf-8'))
                self.scene_description+=f" · Pozycje: {info['rendered_records']}/{info['expected_records']} · Błędy siatki: {len(info['errors'])}"
            names=arr['names']
            self.scene_is_result=Path(path).name=='SCENA_WYNIK.npz' and Path(path).parent==self.result_dir
            for i,c in enumerate(colors):
                rgb=tuple(map(float,c));xyz=vertex[offset[i]:offset[i+1]].astype(np.float32)
                pts=vtkPoints();pts.SetData(numpy_to_vtk(xyz,deep=True))
                n=len(xyz)//3
                cells=np.arange(n*4,dtype=np.int64).reshape(n,4)
                cells[:,0]=3
                cells[:,1:]=np.arange(n*3,dtype=np.int64).reshape(n,3)
                tri=vtkCellArray();tri.SetCells(n,numpy_to_vtkIdTypeArray(cells.ravel(),deep=True))
                poly=vtkPolyData();poly.SetPoints(pts);poly.SetPolys(tri)
                mapper=vtkPolyDataMapper();mapper.SetInputData(poly)
                actor=vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*rgb)
                actor.GetProperty().SetSpecular(0.15);actor.GetProperty().SetSpecularPower(22)
                actor.GetProperty().SetAmbient(0.25);actor.GetProperty().SetDiffuse(0.75)
                actor.GetProperty().SetEdgeColor(0.15,0.20,0.26);actor.GetProperty().SetEdgeVisibility(self.show_edges.isChecked())
                self.renderer.AddActor(actor)
                name=str(names[i]);status,_=metadata(name)
                if name.endswith('[A]') and status not in ('REMOVED',''):actor.GetProperty().SetOpacity(0.25)
                self.body_actors.append((name,actor))
                group=STATUS_NAMES.get(status,'Model')
                if group not in groups:
                    groups[group]=QTreeWidgetItem(self.parts_tree,[group])
                display_name=name.split('] ',2)[-1] if status else name
                item=QTreeWidgetItem(groups[group],[display_name]);item.setData(0,Qt.UserRole,i)
                item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(0,Qt.Checked)
                item.setToolTip(0,name);item.setForeground(0,QColor.fromRgbF(*rgb));self.body_items.append(item)
                hex_color='#'+''.join(f'{min(255,max(0,round(v*255))):02X}' for v in rgb)
                self.viewer_actors.setdefault(hex_color.lower(),[]).append(actor)
            for title,item in groups.items():item.setText(0,f'{title}  ·  {item.childCount()}')
            self.parts_tree.blockSignals(False);self.parts_tree.expandToDepth(0);self.filter_tree()
            self.scene_is_result=Path(path).name=='SCENA_WYNIK.npz' and Path(path).parent==self.result_dir
            self.refresh_legend()
            camera=self.renderer.GetActiveCamera();camera.SetPosition(1.,-1.,0.8);camera.SetFocalPoint(0.,0.,0.);camera.SetViewUp(0.,0.,1.);camera.ParallelProjectionOn()
            self.renderer.ResetCamera()
            self.interactor.Initialize();self.vtk_widget.GetRenderWindow().Render()
            self.refresh_legend()
            self.active_scene=(str(path.resolve()),path.stat().st_mtime_ns)
            self.navigate('viewer')
            self.focus_selected_actor()
        except Exception as exc:
            QMessageBox.critical(self,'Podgląd 3D','Nie można wyświetlić modelu VTK: '+str(exc))

    def closeEvent(self,event):
        if self.process and self.process.state()!=QProcess.NotRunning:
            self.process.kill();self.process.waitForFinished(1000)
        save_settings(self.settings)
        event.accept()


def main(a='',b=''):
    app=QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion')
    w=Window(a,b);w.show()
    return app.exec()
