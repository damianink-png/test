"""DS Compare V3.2 FAST — standalone dark UI for safe STEP B-Rep comparison.

Tkinter only. CAD model operations are NOT performed by the GUI, avoiding
re-entry into ZW3D's command / Windows message loops.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
import traceback
import webbrowser
import re

WERSJA = "3.6"

from .cli import process
from .step_io import COLORS

BG = '#10141B'
SIDEBAR = '#151B24'
CARD = '#1B2430'
CARD_HOVER = '#243040'
INPUT = '#121923'
TEXT = '#F0F3F7'
MUTED = '#9BA8BA'
EDGE = '#283444'
ACCENT = '#E3A13B'
SELECTION = '#344966'
GREEN = '#2DA44E'
PURPLE = '#7465DC'
ORANGE = '#DA9554'

LIGHT_THEME = {'BG':'#F3F6FA','SIDEBAR':'#FFFFFF','CARD':'#FFFFFF','CARD_HOVER':'#E6EDF6',
               'INPUT':'#F1F5FA','TEXT':'#17253A','MUTED':'#61718A','EDGE':'#DCE4F0',
               'ACCENT':'#D78C28','SELECTION':'#DBE6F7'}
DARK_THEME = {'BG':'#0D1420','SIDEBAR':'#111D2D','CARD':'#182638','CARD_HOVER':'#233750',
              'INPUT':'#101B2A','TEXT':'#EAF1F9','MUTED':'#A1B2C8','EDGE':'#2D4059',
              'ACCENT':'#E8A94B','SELECTION':'#325277'}


def use_ui_theme(name):
    colors = LIGHT_THEME if name=='jasny' else DARK_THEME
    globals().update(colors)

COLOR_ROLES = [
    ('SAME', 'Bez zmian', 'Zielony: zgodność geometrii oraz ustawienia'),
    ('ADDED', 'Nowe części', 'Kolor nowych komponentów w B'),
    ('CHANGED', 'Zmieniona geometria', 'Bryły o zmodyfikowanym kształcie'),
    ('MOVED', 'Zmiana położenia', 'Bryła ta sama, inne ustawienie'),
    ('REMOVED', 'Usunięte części', 'Kolor komponentów z modelu A'),
    ('UNCERTAIN', 'Do weryfikacji', 'Niepewne dopasowanie geometryczne'),
]

def _settings_path():
    root = Path(os.environ['APPDATA']) if os.name == 'nt' and os.environ.get('APPDATA') else Path.home() / '.config'
    return root / 'DSCompare' / 'settings.json'

def _valid_hex(value):
    return bool(re.fullmatch(r'#[0-9A-Fa-f]{6}', value))

def _to_triplet(value):
    color = value.lstrip('#')
    return tuple(round(int(color[x:x+2], 16)/255., 6) for x in (0, 2, 4))



def _rgb(color):
    return '#%02X%02X%02X' % tuple(round(max(0.0, min(1.0, x))*255) for x in color)


class ZaokraglonyPrzycisk(tk.Canvas):
    """Lekki przycisk Tk o zaokrąglonych rogach i podświetleniu po najechaniu."""
    def __init__(self, parent, text, command, primary=False, width=None):
        import tkinter.font as tkfont
        self._caption=text
        self._command=command
        self._primary=primary
        self._enabled=True
        self._hover=False
        self._font=tkfont.Font(family='Segoe UI',size=10,weight='bold' if primary else 'normal')
        w=max(92, self._font.measure(text)+34, int(width or 0))
        super().__init__(parent,bg=parent['bg'],highlightthickness=0,bd=0,
                         width=w,height=36,cursor='hand2')
        self.bind('<Enter>',self._enter)
        self.bind('<Leave>',self._leave)
        self.bind('<Button-1>',self._click)
        self.bind('<Configure>',lambda e:self._draw())
        self._draw()
    def _draw(self):
        self.delete('all')
        w=max(2,self.winfo_width());h=max(2,self.winfo_height());r=9
        if self._primary:
            fill='#F6BF72' if self._hover and globals()['BG'] == DARK_THEME['BG'] else ('#EEA43F' if self._hover else ACCENT)
        else:
            fill=SELECTION if self._hover else CARD_HOVER
        if not self._enabled:fill=EDGE
        fg='#182536' if self._primary and self._enabled else (TEXT if self._enabled else MUTED)
        x0,y0,x1,y1=0,0,w-1,h-1
        pts=[x0+r,y0,x1-r,y0,x1,y0,x1,y0+r,x1,y1-r,x1,y1,
             x1-r,y1,x0+r,y1,x0,y1,x0,y1-r,x0,y0+r,x0,y0]
        self.create_polygon(pts,smooth=True,splinesteps=20,fill=fill,outline='')
        self.create_text(w/2,h/2,text=self._caption,font=self._font,fill=fg)
    def _enter(self,_):self._hover=True;self._draw()
    def _leave(self,_):self._hover=False;self._draw()
    def _click(self,_):
        if self._enabled and self._command:self._command()
    def configure(self,cnf=None,**kw):
        if 'state' in kw:
            self._enabled=str(kw.pop('state')) not in ('disabled','DISABLED')
            self._draw()
        if 'text' in kw:self._caption=str(kw.pop('text'));self._draw()
        return super().configure(cnf,**kw)
    config=configure


class GUI(tk.Tk):
    def __init__(self, a='', b='', output=None):
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DS.Szymczyk.DSCompare.V3')
            except (AttributeError, OSError):
                pass
        super().__init__()
        self.title('DS Compare — porównywanie złożeń i geometrii')
        width = min(1240, max(790, self.winfo_screenwidth() - 60))
        height = min(800, max(580, self.winfo_screenheight() - 95))
        self.geometry(f'{width}x{height}')
        self.minsize(790, 575)
        self.configure(bg=BG)
        self.q = queue.Queue()
        self.cancel_requested = False
        self.running = False
        self.a = tk.StringVar(value=a)
        self.mass_input = tk.StringVar()
        self.mass_last_output = None
        self.worker_kind = None
        self.b = tk.StringVar(value=b)
        self.folder = tk.StringVar(value=str(output or Path.home() / 'Documents' / 'DSCompare' / 'Wyniki'))
        self.tolerance = tk.StringVar(value='0.01')
        self.density = tk.StringVar(value='7850')
        self.save_step = tk.BooleanVar(value=True)
        self.diff_step = tk.BooleanVar(value=False)  # Powolne operacje Boolean tylko na życzenie
        self.preview3d = tk.BooleanVar(value=True)
        self.worker = None
        self.open_report = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value='Gotowy do porównania')
        self.last_output = None
        self.views = {}
        self.nav_btns = {}
        self.status_colors = {}
        self.palette_colors = dict(COLORS)
        self.appearance = 'ciemny'
        self._load_settings()
        use_ui_theme(self.appearance)
        self.configure(bg=BG)
        self._set_app_icon()
        self._style()
        self._build()
        self.show_view('compare')
        if os.name == 'nt':
            self.after(100, self._dark_titlebar)
        self.after(130, self.poll)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def _dark_titlebar(self, window=None):
        """Windows 10/11: grafitowy pasek tytułu systemowego, bez własnej ramki."""
        if os.name != 'nt': return
        import ctypes
        target=window or self
        try:
            target.update_idletasks()
            user32=ctypes.windll.user32
            hwnd=user32.GetParent(target.winfo_id()) or target.winfo_id()
            dark=ctypes.c_int(0 if self.appearance=='jasny' else 1)
            for key in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,key,ctypes.byref(dark),ctypes.sizeof(dark))==0:
                    break
            # Kolory caption i tekstu są dostępne w Windows 11.
            caption=ctypes.c_int(0x00FAF6F3 if self.appearance=='jasny' else 0x0020140D)
            foreground=ctypes.c_int(0x003A2517 if self.appearance=='jasny' else 0x00F9F1EA)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,35,ctypes.byref(caption),4)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,36,ctypes.byref(foreground),4)
        except (AttributeError, OSError, ValueError, tk.TclError):
            pass

    def show_about(self):
        window=tk.Toplevel(self)
        window.title('O programie — DS Compare')
        window.configure(bg=BG)
        window.geometry('415x290')
        window.resizable(False,False)
        window.transient(self)
        window.grab_set()
        if os.name == 'nt': self.after(100,lambda:self._dark_titlebar(window))
        tk.Label(window,text='DS Compare',bg=BG,fg=ACCENT,
                 font=('Segoe UI',22,'bold')).pack(anchor='w',padx=26,pady=(25,7))
        tk.Label(window,text='Porównywanie geometrii i złożeń CAD',bg=BG,fg=TEXT,
                 font=('Segoe UI',11)).pack(anchor='w',padx=26)
        tk.Frame(window,bg=EDGE,height=1).pack(fill='x',padx=26,pady=19)
        for key,val in [('Wersja:',WERSJA),('Autor:','Szymczyk Damian'),
                        ('Silnik:','Open CASCADE — analiza B-Rep')]:
            row=tk.Frame(window,bg=BG);row.pack(fill='x',padx=26,pady=3)
            tk.Label(row,text=key,width=11,anchor='w',bg=BG,fg=MUTED,
                     font=('Segoe UI',10)).pack(side='left')
            tk.Label(row,text=val,bg=BG,fg=TEXT,
                     font=('Segoe UI',10)).pack(side='left')
        self._button(window,'Zamknij',window.destroy).pack(anchor='e',padx=26,pady=22)

    def _set_app_icon(self):
        # Windows taskbar icon + icon embedded into EXE via PyInstaller --icon.
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
        png = root / 'assets' / 'DSCompare.png'
        ico = root / 'assets' / 'DSCompare.ico'
        try:
            if png.is_file():
                self._icon_photo = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icon_photo)
            if os.name == 'nt' and ico.is_file():
                self.iconbitmap(default=str(ico))
        except tk.TclError:
            pass

    def _load_settings(self):
        try:
            config = json.loads(_settings_path().read_text(encoding='utf-8'))
            self.appearance = config.get('appearance','ciemny') if config.get('appearance','ciemny') in ('ciemny','jasny') else 'ciemny'
            for role, hex_value in config.get('colors', {}).items():
                if role in COLORS and isinstance(hex_value, str) and _valid_hex(hex_value):
                    self.palette_colors[role] = _to_triplet(hex_value)
            # Renamed parts must share the unchanged status color.
            self.palette_colors['RENAMED'] = self.palette_colors['SAME']
        except (FileNotFoundError, ValueError, OSError, TypeError, KeyError):
            pass

    def _save_settings(self):
        target = _settings_path()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({'appearance':self.appearance,'colors': {k: _rgb(v) for k,v in self.palette_colors.items()}},
                                         indent=2), encoding='utf-8')
        except OSError as exc:
            messagebox.showwarning('DS Compare', 'Nie zapisano ustawień: ' + str(exc))

    def _update_color_views(self):
        for key, button in self.status_colors.items():
            hex_value = _rgb(self.palette_colors[key])
            button.configure(bg=hex_value, activebackground=hex_value)
        for key, (sample, entry_var) in getattr(self, 'settings_colors', {}).items():
            hex_value = _rgb(self.palette_colors[key])
            sample.configure(bg=hex_value, activebackground=hex_value)
            entry_var.set(hex_value)
        for status in ('SAME', 'RENAMED', 'CHANGED', 'MOVED', 'ADDED', 'REMOVED', 'UNCERTAIN'):
            self.tree.tag_configure(status, foreground=_rgb(self.palette_colors[status]))
        for role, widget in getattr(self, 'summary_labels', {}).items():
            target = 'ADDED' if role == 'CHANGED' else role
            widget.configure(fg=_rgb(self.palette_colors[target]))

    def _apply_color(self, key, value):
        if not _valid_hex(value):
            messagebox.showerror('Kolor', 'Podaj kolor w formacie #RRGGBB, np. #2DA44E')
            return
        self.palette_colors[key] = _to_triplet(value)
        if key == 'SAME':
            self.palette_colors['RENAMED'] = self.palette_colors['SAME']
        self._update_color_views()
        self._save_settings()

    def _reset_colors(self):
        self.palette_colors = dict(COLORS)
        self._update_color_views()
        self._save_settings()

    def switch_appearance(self, choice=None):
        if self.running:
            messagebox.showinfo('Motyw', 'Poczekaj na zakończenie analizy przed zmianą motywu.')
            return
        requested=choice or ('jasny' if self.appearance=='ciemny' else 'ciemny')
        if requested == self.appearance:return
        previous=self._current_page
        self.appearance=requested
        self._save_settings()
        use_ui_theme(requested)
        for child in self.winfo_children():child.destroy()
        self.configure(bg=BG)
        self.views={};self.nav_btns={};self.status_colors={};self.settings_colors={}
        self._style();self._build();self.show_view(previous)
        if self.last_output and (self.last_output/'PODSUMOWANIE.json').exists():
            self._load_results(self.last_output)
        if self.mass_last_output and (self.mass_last_output/'PODSUMOWANIE_MASY.json').exists():
            self._load_mass_results(self.mass_last_output)
        if os.name=='nt':self.after(80,self._dark_titlebar)

    def _style(self):
        st = ttk.Style(self)
        st.theme_use('clam')
        st.configure('DS.Treeview', background=INPUT, foreground=TEXT,
                     fieldbackground=INPUT, rowheight=31, borderwidth=0,
                     font=('Segoe UI', 10))
        st.configure('DS.Treeview.Heading', background=CARD_HOVER, foreground=TEXT,
                     font=('Segoe UI', 10, 'bold'), borderwidth=0, relief='flat')
        st.map('DS.Treeview', background=[('selected', SELECTION)], foreground=[('selected', TEXT)])
        st.configure('DS.TCombobox', background=INPUT, foreground=TEXT, fieldbackground=INPUT,
                     arrowcolor=ACCENT, darkcolor=INPUT, lightcolor=INPUT,
                     bordercolor=EDGE, selectbackground=INPUT, selectforeground=TEXT,
                     padding=7)
        st.map('DS.TCombobox', fieldbackground=[('readonly',INPUT)],
               foreground=[('readonly',TEXT)],
               selectbackground=[('readonly',INPUT)], selectforeground=[('readonly',TEXT)])
        self.option_add('*TCombobox*Listbox.background', INPUT)
        self.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground', SELECTION)
        self.option_add('*TCombobox*Listbox.selectForeground', TEXT)
        st.configure('DS.Vertical.TScrollbar', background=CARD_HOVER, troughcolor=BG,
                     bordercolor=BG, arrowcolor=MUTED, relief='flat')
        st.configure('DS.Horizontal.TScrollbar', background=CARD_HOVER, troughcolor=BG,
                     bordercolor=BG, arrowcolor=MUTED, relief='flat')
        st.configure('DS.Horizontal.TProgressbar', troughcolor=INPUT, background=ACCENT,
                     borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

    def _label(self, parent, text, size=10, color=TEXT, weight='normal', **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop('bg', parent['bg']), fg=color,
                        font=('Segoe UI', size, weight), anchor=kwargs.pop('anchor', 'w'), **kwargs)

    def _button(self, parent, text, command, primary=False, width=None):
        return ZaokraglonyPrzycisk(parent,text,command,primary=primary,width=width)

    def _entry(self, parent, variable):
        frame=tk.Frame(parent,bg=INPUT,bd=0)
        entry=tk.Entry(frame,textvariable=variable,bg=INPUT,fg=TEXT,
                       insertbackground=TEXT,relief='flat',bd=0,highlightthickness=0,
                       font=('Segoe UI',10))
        entry.pack(fill='x',expand=True,padx=10,pady=7)
        return frame

    def _card(self, parent, pad=18):
        container = tk.Frame(parent, bg=CARD, bd=0, highlightbackground=EDGE, highlightthickness=1)
        inner = tk.Frame(container, bg=CARD)
        inner.pack(fill='both', expand=True, padx=pad, pady=pad)
        return container, inner

    def _build(self):
        """Nowy, dwukolumnowy panel; karty dopasowują się do szerokości okna."""
        self.left=tk.Frame(self,width=198,bg=SIDEBAR)
        self.left.pack(side='left',fill='y')
        self.left.pack_propagate(False)
        brand=tk.Frame(self.left,bg=SIDEBAR)
        brand.pack(fill='x',padx=18,pady=(24,29))
        logo=tk.Frame(brand,bg=SIDEBAR)
        logo.pack(fill='x')
        self._label(logo,'DS',25,ACCENT,'bold',bg=SIDEBAR).pack(side='left')
        self._label(logo,'COMPARE',15,TEXT,'bold',bg=SIDEBAR).pack(side='left',padx=(8,0),pady=(7,0))
        self._label(brand,'NARZĘDZIA KONSTRUKTORA',8,MUTED,bg=SIDEBAR).pack(anchor='w',pady=(3,0))
        self._label(self.left,'OBSZARY',8,MUTED,'bold',bg=SIDEBAR).pack(anchor='w',padx=21,pady=(0,9))
        for page,title in [('compare','⇄  Porównanie'),('results','▤  Wyniki'),('mass','⚖  Masa części'),
                           ('settings','⚙  Ustawienia'),('log','☷  Dziennik')]:
            btn=tk.Button(self.left,text=title,anchor='w',command=lambda p=page:self.show_view(p),
                          bg=SIDEBAR,fg=MUTED,activebackground=CARD_HOVER,activeforeground=TEXT,
                          relief='flat',bd=0,cursor='hand2',font=('Segoe UI',10),padx=20,pady=11,
                          highlightthickness=0)
            btn.pack(fill='x',padx=9,pady=2)
            self.nav_btns[page]=btn
            btn.bind('<Enter>',lambda _,b=btn:b.configure(bg=CARD_HOVER))
            btn.bind('<Leave>',lambda _,b=btn,n=page:b.configure(bg=CARD_HOVER if self._current_page==n else SIDEBAR))
        sidefooter=tk.Frame(self.left,bg=SIDEBAR)
        sidefooter.pack(side='bottom',fill='x',padx=16,pady=16)
        tk.Frame(sidefooter,bg=EDGE,height=1).pack(fill='x',pady=(0,11))
        self._label(sidefooter,'ZW3D 2019  ·  STEP / STP',8,MUTED,bg=SIDEBAR).pack(anchor='w',pady=(0,9))
        self._button(sidefooter,'ⓘ  O programie',self.show_about).pack(anchor='w')
        workspace=tk.Frame(self,bg=BG)
        workspace.pack(side='left',fill='both',expand=True)
        head=tk.Frame(workspace,bg=BG)
        head.pack(fill='x',padx=25,pady=(18,13))
        heading=tk.Frame(head,bg=BG)
        heading.pack(side='left',fill='x',expand=True)
        self._label(heading,'Porównywanie geometrii CAD',17,TEXT,'bold').pack(anchor='w')
        self._label(heading,'Złożenia · wykrywanie zmian B-Rep · raporty i zestawienia mas',9,MUTED).pack(anchor='w',pady=(3,0))
        appearance=('☾  Motyw ciemny' if self.appearance=='ciemny' else '☼  Motyw jasny')
        self._button(head,appearance,self.switch_appearance).pack(side='right')
        tk.Frame(workspace,bg=EDGE,height=1).pack(fill='x',padx=25)
        content=tk.Frame(workspace,bg=BG)
        content.pack(fill='both',expand=True,padx=25,pady=(14,10))
        for page in ('compare','results','mass','settings','log'):
            item=tk.Frame(content,bg=BG)
            item.place(relx=0,rely=0,relwidth=1,relheight=1)
            self.views[page]=item
        self._build_compare(self.views['compare'])
        self._build_results(self.views['results'])
        self._build_mass(self.views['mass'])
        self._build_settings(self.views['settings'])
        self._build_log(self.views['log'])
        self._update_color_views()

    def _scrolling_page(self, parent):
        """Fit smaller office laptop screens: never hide Analyze/Cancel or color fields."""
        bar = ttk.Scrollbar(parent, orient='vertical')
        bar.pack(side='right', fill='y')
        canvas = tk.Canvas(parent, bg=BG, bd=0, highlightthickness=0,
                           yscrollcommand=bar.set)
        canvas.pack(side='left', fill='both', expand=True)
        bar.configure(command=canvas.yview)
        content = tk.Frame(canvas, bg=BG)
        inner_id = canvas.create_window((0, 0), window=content, anchor='nw')
        content.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(inner_id, width=e.width))
        def wheel(event):
            if getattr(event, 'delta', 0):
                canvas.yview_scroll(-int(event.delta / 120), 'units')
        canvas.bind('<Enter>', lambda _: canvas.bind_all('<MouseWheel>', wheel))
        canvas.bind('<Leave>', lambda _: canvas.unbind_all('<MouseWheel>'))
        return content

    def show_view(self, name):
        self._current_page=name
        self.views[name].tkraise()
        for n, btn in self.nav_btns.items():
            btn.configure(bg=CARD_HOVER if n == name else SIDEBAR,
                          fg=ACCENT if n == name else MUTED)

    def _file_row(self, parent, title, sub, variable, directory=False):
        self._label(parent, title, 11, TEXT, 'bold').pack(anchor='w')
        # Szczegóły pola pokazujemy w podpowiedzi, oszczędzamy miejsce na małych ekranach.
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill='x', pady=(0, 7))
        ef = self._entry(row, variable)
        ef.pack(side='left', fill='x', expand=True)
        self._button(row, 'Wybierz', lambda: self._pick(variable, directory)).pack(side='left', padx=(10, 0))

    def _build_compare(self, host):
        self._label(host, 'Porównaj modele A / B', 14, TEXT, 'bold').pack(anchor='w')
        self._label(host, 'Dokładna analiza geometrii poza ZW3D.',
                    9, MUTED).pack(anchor='w', pady=(1, 7))
        card, body = self._card(host, 11)
        card.pack(fill='x')
        self._file_row(body, 'MODEL A  ·  WERSJA POPRZEDNIA', 'Plik STEP wyeksportowany z ZW3D', self.a)
        self._file_row(body, 'MODEL B  ·  WERSJA AKTUALNA', 'Plik STEP wyeksportowany z ZW3D', self.b)
        self._file_row(body, 'FOLDER WYNIKOWY', 'Raport, BOM A/B, różnice i kolorowy model STEP', self.folder, True)
        params = tk.Frame(body, bg=CARD)
        params.pack(fill='x')
        p1 = tk.Frame(params, bg=CARD)
        p1.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self._label(p1, 'Tolerancja [mm]', 9, MUTED).pack(anchor='w', pady=(0, 5))
        self._entry(p1, self.tolerance).pack(fill='x')
        p2 = tk.Frame(params, bg=CARD)
        p2.pack(side='left', fill='x', expand=True)
        self._label(p2, 'Gęstość [kg/m³]', 9, MUTED).pack(anchor='w', pady=(0, 5))
        self._entry(p2, self.density).pack(fill='x')

        opts = tk.Frame(body, bg=CARD)
        opts.pack(fill='x', pady=(6, 0))
        for label, var in [('Kolorowy STEP (pełny model)', self.save_step), ('Wyznacz dokładne różnice materiału (wolniejsze)', self.diff_step), ('Otwórz raport', self.open_report), ('Podgląd 3D w przeglądarce', self.preview3d)]:
            tk.Checkbutton(opts, text=label, variable=var, bg=CARD, fg=TEXT,
                           activebackground=CARD, activeforeground=TEXT,
                           selectcolor=SIDEBAR, highlightthickness=0,
                           font=('Segoe UI', 9)).pack(side='left', padx=(0, 12))

        legend = tk.Frame(host, bg=BG)
        legend.pack(fill='x', pady=(8, 6))
        self._label(legend, 'KOLORY PORÓWNANIA', 9, MUTED, 'bold').pack(anchor='w', pady=(0, 7))
        swatches = tk.Frame(legend, bg=BG)
        swatches.pack(fill='x')
        for key, desc in [('SAME', 'Bez zmian'), ('CHANGED', 'Zmienione'),
                          ('REMOVED', 'Usunięte'), ('UNCERTAIN', 'Do sprawdzenia')]:
            group = tk.Frame(swatches, bg=BG)
            group.pack(side='left', padx=(0, 17))
            btn = tk.Button(group, bg=_rgb(self.palette_colors[key]), activebackground=_rgb(self.palette_colors[key]),
                            width=2, height=1, relief='flat', bd=0,
                            command=lambda k=key: self._choose_color(k), cursor='hand2')
            btn.pack(side='left', padx=(0, 6))
            self.status_colors[key] = btn
            self._label(group, desc, 9, MUTED).pack(side='left')

        self._button(legend, 'Zmień kolory / zapamiętaj ustawienia   →',
                     lambda: self.show_view('settings')).pack(anchor='w', pady=(8, 0))

        actions = tk.Frame(host, bg=BG)
        actions.pack(fill='x', pady=(3, 5))
        self.run_button = self._button(actions, 'PORÓWNAJ B-REP', self.start, primary=True)
        self.run_button.pack(side='left')
        self.stop_button = self._button(actions, 'Anuluj', self.cancel)
        self.stop_button.pack(side='left', padx=8)
        self.stop_button.configure(state='disabled')
        self._button(actions, 'Otwórz wyniki', self.open_folder).pack(side='right')
        self.progress = ttk.Progressbar(host, mode='indeterminate', style='DS.Horizontal.TProgressbar')
        self.status_label = tk.Label(host, textvariable=self.status_text, bg=BG, fg=MUTED,
                                     anchor='w', font=('Segoe UI', 9))
        self.status_label.pack(fill='x', pady=(4,0))

    def _build_results(self, host):
        self._label(host, 'Wyniki porównania', 14, TEXT, 'bold').pack(anchor='w')
        self._label(host, 'Lista wykrytych zmian z raportu — wyniki są aktualizowane po zakończeniu analizy.',
                    9, MUTED).pack(anchor='w', pady=(3, 14))
        self.summary_frame = tk.Frame(host, bg=BG)
        self.summary_frame.pack(fill='x', pady=(0, 13))
        self.summary_labels = {}
        for key, title, color in [('SAME', 'BEZ ZMIAN', GREEN), ('CHANGED', 'NOWE / ZMIENIONE', PURPLE),
                                   ('REMOVED', 'USUNIĘTE', ORANGE), ('UNCERTAIN', 'NIEPEWNE', MUTED)]:
            card = tk.Frame(self.summary_frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
            card.pack(side='left', expand=True, fill='x', padx=(0, 9))
            number = self._label(card, '—', 24, color, 'bold')
            number.pack(anchor='w', padx=14, pady=(10, 0))
            self._label(card, title, 8, MUTED).pack(anchor='w', padx=14, pady=(0, 12))
            self.summary_labels[key] = number
        filter_row = tk.Frame(host, bg=BG)
        filter_row.pack(fill='x', pady=(0, 9))
        self._label(filter_row, 'Filtruj wyniki:', 9, MUTED).pack(side='left', padx=(0, 9))
        self.search_results = tk.StringVar()
        self.search_results.trace_add('write', lambda *_: self._filter_results())
        self._entry(filter_row, self.search_results).pack(side='left', fill='x', expand=True)
        self.filter_status = tk.StringVar(value='Wszystkie')
        statuses = ('Wszystkie','Bez zmian','Zmieniona geometria','Przesunięte','Nowe','Usunięte','Niepewne')
        self.filter_box = ttk.Combobox(filter_row, textvariable=self.filter_status,
                                       values=statuses, state='readonly', width=21)
        self.filter_box.configure(style='DS.TCombobox')
        self.filter_box.pack(side='left', padx=(10, 0))
        self.filter_box.bind('<<ComboboxSelected>>', lambda _: self._filter_results())
        self._all_result_rows = []
        frame = tk.Frame(host, bg=CARD, padx=0, pady=0)
        frame.pack(fill='both', expand=True)
        cols = ('status', 'a', 'b', 'delta', 'note')
        tree = ttk.Treeview(frame, columns=cols, show='headings', style='DS.Treeview',height=5)
        for key, title, width in [('status', 'Status', 115), ('a', 'Nazwa A', 125),
                                  ('b', 'Nazwa B', 125), ('delta', 'Przes. [mm]', 100),
                                  ('note', 'Uwagi', 240)]:
            tree.heading(key, text=title)
            tree.column(key, width=width, stretch=(key == 'note'))
        bar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview, style='DS.Vertical.TScrollbar')
        hbar = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview, style='DS.Horizontal.TScrollbar')
        tree.configure(yscrollcommand=bar.set, xscrollcommand=hbar.set)
        bar.pack(side='right', fill='y')
        hbar.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)
        for status in ('SAME','RENAMED','CHANGED','MOVED','ADDED','REMOVED','UNCERTAIN'):
            tree.tag_configure(status, foreground=_rgb(self.palette_colors[status]))
        self.tree = tree
        self.detail_var = tk.StringVar(value='Zaznacz wiersz, aby odczytać pełną nazwę i szczegóły zmiany.')
        self._label(host, 'SZCZEGÓŁY WYBRANEJ ZMIANY', 9, MUTED, 'bold').pack(anchor='w', pady=(10,3))
        tk.Label(host,textvariable=self.detail_var, bg=BG, fg=TEXT,
                 anchor='w', justify='left', wraplength=700,
                 font=('Segoe UI',9)).pack(fill='x')
        tree.bind('<<TreeviewSelect>>', self._show_detail)
        buttons = tk.Frame(host, bg=BG)
        buttons.pack(fill='x', pady=(5,3))
        self._button(buttons, 'Raport HTML', self.open_report_file, primary=True).pack(side='left')
        self._button(buttons, 'Folder wynikowy', self.open_folder).pack(side='left', padx=8)
        self._button(buttons, 'Kolorowy STEP', self.open_step_file).pack(side='left')
        self._button(buttons, 'Podgląd 3D', self.open_preview_file).pack(side='left',padx=8)
        self._button(buttons, 'Otwórz w…', self.open_step_with).pack(side='left',padx=(8,0))
        self._button(buttons, 'Tylko różnice', self.open_differences_file).pack(side='left',padx=8)

    def _build_mass(self, host):
        self._label(host, 'Masa części — jeden model STEP', 14, TEXT, 'bold').pack(anchor='w')
        self._label(host, 'Wczytaj jeden plik, policz bryły i wygeneruj zestawienie mas. Bez porównania B-Rep.',
                    9, MUTED).pack(anchor='w', pady=(3, 13))
        card, body=self._card(host,14);card.pack(fill='x')
        self._file_row(body, 'MODEL STEP / STP', 'Model do obliczeń', self.mass_input)
        row=tk.Frame(body,bg=CARD);row.pack(fill='x', pady=(3, 0))
        self._label(row, 'Gęstość materiału [kg/m³]:', 10, MUTED).pack(side='left',padx=(0, 12))
        mass_density_entry=self._entry(row,self.density)
        mass_density_entry.pack(side='left',fill='x',expand=False)
        self._label(row, 'Przykład: stal 7850 kg/m³',9,MUTED).pack(side='left',padx=13)
        actions=tk.Frame(host,bg=BG);actions.pack(fill='x',pady=(13,13))
        self.mass_run_button=self._button(actions,'OBLICZ MASY',self.start_mass,primary=True)
        self.mass_run_button.pack(side='left')
        self._button(actions,'Otwórz CSV',lambda:self._open_path(self.mass_last_output/'MASY_CZESCI.csv' if self.mass_last_output else None)).pack(side='left',padx=9)
        self._button(actions,'Raport HTML',lambda:self._open_path(self.mass_last_output/'RAPORT_MASY.html' if self.mass_last_output else None)).pack(side='left')
        self.mass_summary=tk.StringVar(value='Oczekiwanie na model STEP.')
        self._label(host,'PODSUMOWANIE',10,MUTED,'bold').pack(anchor='w',pady=(4,5))
        tk.Label(host,textvariable=self.mass_summary,bg=BG,fg=TEXT,font=('Segoe UI',11),anchor='w').pack(fill='x',pady=(0,12))
        frame=tk.Frame(host,bg=CARD);frame.pack(fill='both',expand=True)
        columns=('name','qty','unit','total')
        tree=ttk.Treeview(frame,columns=columns,show='headings',style='DS.Treeview',height=5)
        for key,title,w in [('name','Nazwa części',340),('qty','Ilość',75),
                            ('unit','Masa jednej sztuki [kg]',175),('total','Masa łączna [kg]',180)]:
            tree.heading(key,text=title);tree.column(key,width=w,stretch=(key=='name'),minwidth=65)
        scrollbar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview,style='DS.Vertical.TScrollbar')
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
        self.mass_tree=tree
        self._label(host,'Masa jest obliczana z objętości brył i podanej gęstości. Nie odczytujemy materiału z Z3.',
                    9,MUTED).pack(anchor='w',pady=(10,4))

    def start_mass(self):
        if self.running:return
        try:
            model=Path(self.mass_input.get())
            if not model.is_file() or model.suffix.lower() not in ('.step','.stp'):
                raise ValueError('Wskaż istniejący plik STEP lub STP.')
            density=float(self.density.get().replace(',','.'))
            if not 0<density<=25000:raise ValueError('Gęstość poza zakresem (0, 25000] kg/m³.')
        except Exception as exc:
            messagebox.showerror('Masa części',str(exc));return
        self.running=True;self.cancel_requested=False;self.worker_kind='mass'
        self.mass_run_button.configure(state='disabled')
        self.status_text.set('Obliczanie mas jednego modelu...')
        self.mass_summary.set('Trwa wczytywanie brył i obliczanie mas...')
        self.show_view('mass')
        args=[sys.executable]
        if not getattr(sys,'frozen',False):args.append(str(Path(__file__).resolve().parents[1]/'DSCompareV3.py'))
        args += ['--dscompare-mass-worker','--single',str(model),
                 '--output',str(Path(self.folder.get())/'MASA_JEDNEGO_MODELU'),
                 '--density',str(density)]
        try:
            self.worker=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                encoding='utf-8',errors='replace',text=True,bufsize=1,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception as exc:
            self._finish();messagebox.showerror('Masa części','Błąd uruchomienia: '+str(exc));return
        self._follow_worker(self.worker)

    def _load_mass_results(self,folder):
        folder=Path(folder);self.mass_last_output=folder
        summary=json.loads((folder/'PODSUMOWANIE_MASY.json').read_text(encoding='utf-8'))
        def num(x):return f'{x:,.3f}'.replace(',',' ').replace('.',',')
        self.mass_summary.set(f"{summary['liczba_bryl']} brył  ·  {summary['liczba_pozycji']} pozycji  ·  masa całkowita {num(summary['masa_calosci_kg'])} kg")
        for item in self.mass_tree.get_children():self.mass_tree.delete(item)
        with (folder/'MASY_CZESCI.csv').open(encoding='utf-8-sig',newline='') as f:
            for record in csv.DictReader(f,delimiter=';'):
                values=(self._display_csv_name(record.get('Nazwa części','')),
                        record.get('Ilość',''),record.get('Masa jednej sztuki [kg]',''),
                        record.get('Masa łączna [kg]',''))
                self.mass_tree.insert('','end',values=values)

    def _build_log(self, host):
        self._label(host, 'Dziennik analizy', 14, TEXT, 'bold').pack(anchor='w')
        self._label(host, 'Szczegółowe informacje i błędy operacji geometrycznych.', 9, MUTED).pack(anchor='w', pady=(3, 12))
        self.log = tk.Text(host, bg=INPUT, fg=TEXT, font=('Consolas', 10),
                           insertbackground=TEXT, wrap='word', bd=0,
                           highlightthickness=1, highlightbackground=EDGE, padx=12, pady=12)
        self.log.pack(fill='both', expand=True)
        self._button(host, 'Wyczyść dziennik', lambda: self.log.delete('1.0', 'end')).pack(anchor='w', pady=12)

    def _pick(self, variable, isdir=False):
        path = filedialog.askdirectory() if isdir else filedialog.askopenfilename(
            filetypes=[('Modele STEP / STP', '*.step *.stp'), ('Wszystkie pliki', '*.*')])
        if path:
            variable.set(path)

    def _build_settings(self, host):
        self._label(host, 'Wygląd i kolory modeli', 14, TEXT, 'bold').pack(anchor='w')
        self._label(host, 'Motyw jasny / ciemny zmienisz przyciskiem w nagłówku. Kolory zapisują się automatycznie.',
                    9, MUTED).pack(anchor='w', pady=(2, 7))
        card, body = self._card(host, 10)
        card.pack(fill='x')
        self.settings_colors = {}
        for index, (role, title, desc) in enumerate(COLOR_ROLES):
            row = tk.Frame(body, bg=CARD)
            row.pack(fill='x', pady=3)
            sample = tk.Button(row, bg=_rgb(self.palette_colors[role]), relief='flat', bd=0,
                               width=3, height=1, cursor='hand2',
                               command=lambda k=role: self._choose_color(k))
            sample.pack(side='left', padx=(0, 14))
            words = tk.Frame(row, bg=CARD)
            words.pack(side='left', fill='x', expand=True)
            self._label(words, title, 10, TEXT, 'bold').pack(anchor='w')
            self._label(words, desc, 9, MUTED).pack(anchor='w')
            value = tk.StringVar(value=_rgb(self.palette_colors[role]))
            entry = tk.Entry(row, textvariable=value, bg=INPUT, fg=TEXT, width=11,
                             relief='flat', insertbackground=TEXT, justify='center',
                             font=('Consolas', 10))
            entry.pack(side='left', padx=(8, 7), ipady=6)
            entry.bind('<Return>', lambda event, k=role, v=value: self._apply_color(k,v.get()))
            self._button(row, 'Zapisz', lambda k=role,v=value: self._apply_color(k,v.get())).pack(side='left')
            self.settings_colors[role] = sample, value
        actions = tk.Frame(host, bg=BG)
        actions.pack(fill='x', pady=8)
        self._button(actions, 'Przywróć domyślne', self._reset_colors).pack(side='left')
        self._button(actions, 'Wróć do porównania', lambda: self.show_view('compare'),
                     primary=True).pack(side='right')
        self._label(host, 'Kolory obejmują pełny STEP, plik różnic i raport.\n'
                          'Kolory detali bez zmian i ze zmienioną nazwą są zawsze wspólne.',
                    9, MUTED).pack(anchor='w', pady=10)

    def _choose_color(self, key):
        picked = colorchooser.askcolor(color=_rgb(self.palette_colors[key]), title='DS Compare — kolor '+key)
        if picked and picked[1]:
            self._apply_color(key, picked[1].upper())

    def start(self):
        if self.running:
            return
        try:
            aa, bb = Path(self.a.get()), Path(self.b.get())
            for path in (aa, bb):
                if not path.is_file() or path.suffix.lower() not in ('.step', '.stp'):
                    raise ValueError('Wskaż dwa istniejące pliki STEP lub STP.')
            if aa.resolve() == bb.resolve():
                raise ValueError('Model A i B muszą być różnymi plikami.')
            tol = float(self.tolerance.get().replace(',', '.'))
            density = float(self.density.get().replace(',', '.'))
            if not (0 < tol <= 1): raise ValueError('Tolerancja musi wynosić >0 i ≤1 mm.')
            if not (0 < density <= 25000): raise ValueError('Gęstość poza zakresem (0, 25000] kg/m³.')
            out = Path(self.folder.get())
            if not str(out).strip(): raise ValueError('Wybierz folder wynikowy.')
            if out.resolve() in (aa.resolve(), bb.resolve()):
                raise ValueError('Niepoprawny folder wynikowy.')
        except Exception as exc:
            messagebox.showerror('Niepoprawne dane', str(exc))
            return
        self.running = True
        self.cancel_requested = False
        self.worker_kind = 'compare'
        self.run_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.status_text.set('Trwa analiza geometrii B-Rep…')
        self.progress.pack(fill='x', pady=(3,2), before=self.status_label)
        self.progress.start(12)
        self.show_view('log')
        self.log.delete('1.0', 'end')
        colors = dict(self.palette_colors)
        args=[sys.executable]
        if not getattr(sys,'frozen',False):
            args += [str(Path(__file__).resolve().parents[1]/'DSCompareV3.py')]
        args += ['--dscompare-worker','--a',str(aa),'--b',str(bb),'--output',str(out),
                 '--tolerance',str(tol),'--density',str(density),
                 '--colors-json',json.dumps(colors)]
        if not self.save_step.get():args.append('--no-main-step')
        if not self.diff_step.get():args.append('--no-diff-step')
        if not self.preview3d.get():args.append('--no-preview-3d')
        try:
            self.worker=subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                encoding='utf-8',errors='replace',text=True,bufsize=1,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception as exc:
            self._finish()
            messagebox.showerror('DS Compare','Uruchomienie silnika nieudane: '+str(exc))
            return
        self._follow_worker(self.worker)

    def _follow_worker(self,proc):
        def follow(proc):
            done=None; fail=None
            try:
                for line in proc.stdout:
                    if line.startswith('DSCOMPARE_EVENT:'):
                        try:
                            event=json.loads(line[len('DSCOMPARE_EVENT:'):])
                            typ=event.get('type')
                            if typ=='log':self.q.put(('message',str(event.get('value',''))))
                            elif typ=='done':done=('done',event['folder'],event.get('error'))
                            elif typ=='error':fail=str(event.get('value'))
                        except Exception as exc:
                            self.q.put(('message','Komunikat silnika: '+str(exc)))
                    else:self.q.put(('message',line.rstrip()))
                ret=proc.wait()
                if self.cancel_requested:self.q.put(('cancelled',))
                elif ret==0 and done:self.q.put(done)
                else:self.q.put(('error',fail or f'Silnik zakończył działanie kodem {ret}.'))
            except Exception:self.q.put(('error',traceback.format_exc()))
        threading.Thread(target=follow,args=(self.worker,),daemon=True).start()

    def cancel(self):
        if not self.running:return
        self.cancel_requested=True
        self.q.put(('message','Zatrzymywanie niezależnego procesu B-Rep...'))
        if self.worker and self.worker.poll() is None:
            try:self.worker.terminate()
            except OSError:pass

    def close_app(self):
        if self.worker and self.worker.poll() is None:
            try:self.worker.terminate()
            except OSError:pass
        self.destroy()

    def _finish(self):
        self.running = False
        self.run_button.configure(state='normal')
        self.mass_run_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.progress.stop()
        self.progress.pack_forget()

    def _show_detail(self, _event=None):
        selection = self.tree.selection()
        if not selection:return
        values = self.tree.item(selection[0], 'values')
        if not values:return
        self.detail_var.set(f'{values[0]} | A: {values[1] or "—"} | B: {values[2] or "—"}\n{values[4]}')

    @staticmethod
    def _display_csv_name(name):
        # CSV zabezpiecza numer z początkowym zerem jako formułę Excel,
        # lecz takiego zapisu nie należy pokazywać w tabeli programu.
        name=str(name or '')
        if name.startswith('="') and name.endswith('"'):
            return name[2:-1]
        return name

    def _load_results(self, folder):
        out = Path(folder)
        with (out / 'PODSUMOWANIE.json').open(encoding='utf-8') as inp:
            data = json.load(inp)
        counts = data.get('statuses', {})
        for key, widget in self.summary_labels.items():
            amount = counts.get(key, 0)
            if key == 'SAME': amount += counts.get('RENAMED', 0)
            if key == 'CHANGED': amount += counts.get('MOVED', 0) + counts.get('ADDED', 0)
            widget.configure(text=str(amount))
        self._all_result_rows = []
        with (out / 'ZMIANY.csv').open(encoding='utf-8-sig', newline='') as inp:
            for row in csv.DictReader(inp, delimiter=';'):
                state = {
                    'Bez zmian':'SAME','Bez zmian — zmieniona nazwa':'RENAMED',
                    'Zmiana położenia/obrotu':'MOVED','Zmieniona geometria':'CHANGED',
                    'Nowy':'ADDED','Usunięty':'REMOVED',
                    'Wymaga weryfikacji':'UNCERTAIN'
                }.get(row.get('Rodzaj zmiany', ''), 'UNCERTAIN')
                short = {'SAME':'Bez zmian','RENAMED':'Nowa nazwa','MOVED':'Przesunięty',
                         'CHANGED':'Geometria','ADDED':'Nowy','REMOVED':'Usunięty',
                         'UNCERTAIN':'Niepewny'}.get(state, state)
                values = (short, self._display_csv_name(row.get('Nazwa A', '')), self._display_csv_name(row.get('Nazwa B', '')),
                          row.get('Przesunięcie środka [mm]', ''), row.get('Uwagi', ''))
                self._all_result_rows.append((values,state))
        self._filter_results()

    def _filter_results(self):
        tree = getattr(self, 'tree', None)
        if tree is None: return
        for item in tree.get_children(): tree.delete(item)
        needle = self.search_results.get().casefold().strip()
        selection = self.filter_status.get()
        allowed = {'Bez zmian': ('SAME','RENAMED'),
                   'Zmieniona geometria': ('CHANGED',),
                   'Przesunięte': ('MOVED',),
                   'Nowe': ('ADDED',), 'Usunięte': ('REMOVED',),
                   'Niepewne': ('UNCERTAIN',)}.get(selection)
        for values,state in self._all_result_rows:
            if allowed is not None and state not in allowed:continue
            if needle and needle not in ' '.join(values).casefold():continue
            tree.insert('', 'end', values=values, tags=(state,))

    def poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == 'message':
                    self.log.insert('end', msg[1] + '\n')
                    self.log.see('end')
                    self.status_text.set(msg[1])
                elif msg[0] == 'done':
                    self._finish()
                    self.last_output = Path(msg[1])
                    if self.worker_kind == 'mass':
                        self._load_mass_results(self.last_output)
                        self.status_text.set('Obliczanie mas zakończone')
                        self.show_view('mass')
                    else:
                        self._load_results(self.last_output)
                        self.status_text.set('Porównanie zakończone')
                        self.show_view('results')
                        if self.open_report.get(): self.open_report_file()
                        if msg[2]: messagebox.showwarning('STEP — ostrzeżenie', str(msg[2]))
                elif msg[0] == 'cancelled':
                    self._finish()
                    self.status_text.set('Analiza anulowana')
                elif msg[0] == 'error':
                    self._finish()
                    self.status_text.set('Błąd analizy — sprawdź dziennik')
                    self.log.insert('end', msg[1] + '\n')
                    self.log.see('end')
                    self.show_view('log')
                    messagebox.showerror('Błąd analizy', msg[1][-1300:])
        except queue.Empty:
            pass
        self.after(130, self.poll)

    def _open_path(self, path):
        if not path or not Path(path).exists():
            messagebox.showinfo('DS Compare', 'Plik wynikowy nie został jeszcze utworzony.')
            return
        if os.name == 'nt': os.startfile(str(path))
        else: webbrowser.open(Path(path).as_uri())

    def open_folder(self):
        path = self.last_output or Path(self.folder.get())
        Path(path).mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    def open_report_file(self):
        self._open_path(self.last_output / 'RAPORT.html' if self.last_output else None)

    def open_preview_file(self):
        self._open_path(self.last_output / 'PODGLAD_KOLOROW_3D.html' if self.last_output else None)

    def open_step_file(self):
        self._open_path(self.last_output / 'POROWNANIE_KOLORY.step' if self.last_output else None)

    def open_step_with(self):
        path = self.last_output / 'POROWNANIE_KOLORY.step' if self.last_output else None
        if not path or not path.exists():
            messagebox.showinfo('DS Compare','Nie znaleziono kolorowego modelu STEP.')
            return
        if os.name == 'nt':
            try:
                # Systemowe okno "Otwórz za pomocą" pozwala wybrać ZW3D zamiast CADbro.
                subprocess.Popen(['rundll32.exe','shell32.dll,OpenAs_RunDLL',str(path)],
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            except OSError as exc:messagebox.showerror('DS Compare',str(exc))
        else:self._open_path(path)

    def open_differences_file(self):
        self._open_path(self.last_output / 'ROZNICE_BREP.step' if self.last_output else None)


def _mass_worker_main(argv=None):
    from .single_mass import analyze_single
    p=argparse.ArgumentParser()
    p.add_argument('--dscompare-mass-worker',action='store_true')
    p.add_argument('--single',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--density',type=float,default=7850.0)
    args=p.parse_args(argv)
    def emit(kind,**kwargs):
        print('DSCOMPARE_EVENT:'+json.dumps({'type':kind,**kwargs},ensure_ascii=True),flush=True)
    try:
        folder,_=analyze_single(args.single,args.output,args.density,
                                progress=lambda s:emit('log',value=s))
        emit('done',folder=str(folder),error=None)
        return 0
    except Exception:
        emit('error',value=traceback.format_exc())
        return 1

def _worker_main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--dscompare-worker',action='store_true')
    for k in ('a','b','output'):p.add_argument('--'+k,required=True)
    p.add_argument('--tolerance',type=float,default=0.01)
    p.add_argument('--density',type=float,default=7850.)
    p.add_argument('--colors-json',default='{}')
    p.add_argument('--no-main-step',action='store_true')
    p.add_argument('--no-diff-step',action='store_true')
    p.add_argument('--no-preview-3d',action='store_true')
    args=p.parse_args(argv)
    def emit(kind,**kwargs):
        print('DSCOMPARE_EVENT:'+json.dumps({'type':kind,**kwargs},ensure_ascii=True),flush=True)
    try:
        folder,rows,err=process(args.a,args.b,args.output,args.tolerance,args.density,
            not args.no_main_step,progress=lambda s:emit('log',value=s),
            colors=json.loads(args.colors_json),diff_step=not args.no_diff_step,preview3d=not args.no_preview_3d)
        emit('done',folder=str(folder),error=err)
        return 0
    except Exception:
        emit('error',value=traceback.format_exc());return 1


def main(argv=None):
    if '--dscompare-mass-worker' in (sys.argv[1:] if argv is None else argv):
        return _mass_worker_main(argv)
    if '--dscompare-worker' in (sys.argv[1:] if argv is None else argv):
        return _worker_main(argv)
    p = argparse.ArgumentParser(description='DS Compare — porównywanie geometrii')
    p.add_argument('--a', default='', help='Wstępnie wybrany model A STEP')
    p.add_argument('--b', default='', help='Wstępnie wybrany model B STEP')
    p.add_argument('--output', default=None, help='Folder wyników')
    opt = p.parse_args(argv)
    GUI(a=opt.a, b=opt.b, output=opt.output).mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
