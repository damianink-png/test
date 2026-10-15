"""DS Compare V3.0: independent STEP B-Rep comparison, styled after DS Estimate."""
import argparse, csv, json, os, queue, threading, traceback, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dsac29.cli import process

BG="#10151e"; SIDE="#141c28"; CARD="#1d2937"; FG="#ecf1f7"; MUTED="#9caabc"; GOLD="#e3a13b"

class App(tk.Tk):
    def __init__(self, a="", b=""):
        super().__init__()
        self.title("DS Compare V3.0 — Geometry & Assembly Comparison")
        self.geometry("1050x760"); self.minsize(870,670); self.configure(bg=BG)
        self.a=tk.StringVar(value=a);self.b=tk.StringVar(value=b)
        self.output=tk.StringVar(value=str(Path.home()/"Documents"/"DSCompare"/"Wyniki"))
        self.tolerance=tk.StringVar(value="0.01");self.density=tk.StringVar(value="7850")
        self.save_step=tk.BooleanVar(value=True);self.status=tk.StringVar(value="Gotowy do analizy")
        self.q=queue.Queue(); self.cancel_flag=threading.Event();self.busy=False;self.result=None
        self.build(); self.after(120,self.poll)
    def txt(self,parent,value,size=10,color=FG,bold=False):
        return tk.Label(parent,text=value,bg=parent["bg"],fg=color,anchor="w",
                        font=("Segoe UI",size,"bold" if bold else "normal"))
    def button(self,parent,title,fn,primary=False):
        return tk.Button(parent,text=title,command=fn,bg=GOLD if primary else CARD,
                         fg=BG if primary else FG,activebackground="#f2b75a" if primary else "#344358",
                         relief="flat",bd=0,font=("Segoe UI",10,"bold"),padx=17,pady=10,cursor="hand2")
    def build(self):
        left=tk.Frame(self,bg=SIDE,width=210);left.pack(side="left",fill="y");left.pack_propagate(False)
        self.txt(left,"DS",27,GOLD,True).pack(anchor="w",padx=20,pady=(22,0))
        self.txt(left,"COMPARE",20,FG,True).pack(anchor="w",padx=20)
        self.txt(left,"GEOMETRY / B-REP",9,MUTED).pack(anchor="w",padx=20,pady=(5,24))
        for key,title in [("compare","Porównanie"),("results","Wyniki"),("log","Dziennik")]:
            self.button(left,title,lambda name=key:self.open_tab(name)).pack(fill="x",padx=12,pady=4)
        signature=tk.Frame(left,bg=SIDE);signature.pack(side="bottom",fill="x",padx=20,pady=23)
        self.txt(signature,"DS Compare V3.0",9,GOLD,True).pack(anchor="w")
        self.txt(signature,"Designed & developed by",8,MUTED).pack(anchor="w",pady=(12,0))
        self.txt(signature,"Szymczyk Damian",9,FG).pack(anchor="w")
        right=tk.Frame(self,bg=BG);right.pack(fill="both",expand=True)
        self.txt(right,"Geometry & Assembly Comparison",18,FG,True).pack(anchor="w",padx=25,pady=(22,7))
        self.txt(right,"B-REP  •  STEP/STP  •  ZW3D 2019",9,GOLD,True).pack(anchor="w",padx=25,pady=(0,15))
        content=tk.Frame(right,bg=BG);content.pack(fill="both",expand=True,padx=25,pady=(4,16))
        self.tabs={}
        for name in ("compare","results","log"):
            f=tk.Frame(content,bg=BG);f.place(relx=0,rely=0,relwidth=1,relheight=1);self.tabs[name]=f
        self.compare_tab();self.results_tab();self.log_tab();self.open_tab("compare")
    def open_tab(self,name):self.tabs[name].tkraise()
    def input_line(self,holder,title,var,folder=False):
        self.txt(holder,title,10,FG,True).pack(anchor="w",pady=(13,5))
        row=tk.Frame(holder,bg=CARD);row.pack(fill="x")
        ent=tk.Entry(row,textvariable=var,bg="#101925",fg=FG,insertbackground=FG,
                     relief="flat",font=("Segoe UI",10));ent.pack(side="left",fill="x",expand=True,ipady=12,padx=8)
        def choose():
            p=filedialog.askdirectory() if folder else filedialog.askopenfilename(filetypes=[("STEP/STP","*.step *.stp"),("Wszystkie","*.*")])
            if p:var.set(p)
        self.button(row,"Wybierz",choose).pack(side="right")
    def compare_tab(self):
        tab=self.tabs["compare"]
        self.txt(tab,"Porównaj dwa modele",16,FG,True).pack(anchor="w")
        self.txt(tab,"Dokładna geometria B-Rep, analiza poza procesem ZW3D.",9,MUTED).pack(anchor="w",pady=(3,12))
        card=tk.Frame(tab,bg=CARD);card.pack(fill="x")
        body=tk.Frame(card,bg=CARD);body.pack(fill="x",padx=17,pady=(4,17))
        self.input_line(body,"MODEL A  /  WERSJA POPRZEDNIA",self.a)
        self.input_line(body,"MODEL B  /  WERSJA AKTUALNA",self.b)
        self.input_line(body,"KATALOG RAPORTÓW",self.output,True)
        cfg=tk.Frame(body,bg=CARD);cfg.pack(fill="x",pady=(15,4))
        for title,var in [("Tolerancja [mm]",self.tolerance),("Gęstość [kg/m³]",self.density)]:
            group=tk.Frame(cfg,bg=CARD);group.pack(side="left",padx=(0,20))
            self.txt(group,title,9,MUTED).pack(anchor="w")
            tk.Entry(group,textvariable=var,width=12,bg="#101925",fg=FG,relief="flat",
                     insertbackground=FG).pack(ipady=7,pady=5)
        tk.Checkbutton(body,text="Eksportuj kolorowy STEP",variable=self.save_step,bg=CARD,
                       fg=FG,selectcolor="#101925",activebackground=CARD).pack(anchor="w",pady=5)
        legend=tk.Frame(tab,bg=BG);legend.pack(fill="x",pady=(13,9))
        for color,title in [("#2da44e","Bez zmian"),("#7465dc","Nowe / zmienione"),("#da9554","Usunięte")]:
            self.txt(legend,"●",15,color).pack(side="left")
            self.txt(legend,title,9,MUTED).pack(side="left",padx=(0,17))
        actions=tk.Frame(tab,bg=BG);actions.pack(fill="x",pady=7)
        self.go=self.button(actions,"PORÓWNAJ B-REP",self.run,True);self.go.pack(side="left")
        self.stop=self.button(actions,"Anuluj",lambda:self.cancel_flag.set());self.stop.pack(side="left",padx=8);self.stop.config(state="disabled")
        self.button(actions,"Otwórz folder",self.open_folder).pack(side="right")
        self.progress=ttk.Progressbar(tab,mode="indeterminate");self.progress.pack(fill="x",pady=(12,8))
        tk.Label(tab,textvariable=self.status,bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w")
    def results_tab(self):
        tab=self.tabs["results"];self.txt(tab,"Wyniki porównania",16,FG,True).pack(anchor="w",pady=(0,13))
        summary=tk.Frame(tab,bg=BG);summary.pack(fill="x",pady=(0,16))
        self.numbers={}
        for key,name in [("SAME","Bez zmian"),("CHANGED","Nowe / zmienione"),("REMOVED","Usunięte"),("UNCERTAIN","Niepewne")]:
            c=tk.Frame(summary,bg=CARD);c.pack(side="left",fill="x",expand=True,padx=(0,6))
            val=self.txt(c,"—",23,FG,True);val.pack(padx=12,pady=(12,1));self.numbers[key]=val
            self.txt(c,name,9,MUTED).pack(padx=12,pady=(0,13))
        style=ttk.Style(self);style.theme_use("clam")
        style.configure("Dark.Treeview",background="#111b26",foreground=FG,
                        fieldbackground="#111b26",rowheight=30,font=("Segoe UI",9))
        style.configure("Dark.Treeview.Heading",background=CARD,foreground=FG,font=("Segoe UI",9,"bold"))
        cols=("Status","A","B","Uwagi")
        self.grid=ttk.Treeview(tab,columns=cols,show="headings",style="Dark.Treeview")
        for c in cols:self.grid.heading(c,text=c);self.grid.column(c,minwidth=80,width=150,stretch=True)
        self.grid.pack(fill="both",expand=True)
        controls=tk.Frame(tab,bg=BG);controls.pack(fill="x",pady=11)
        self.button(controls,"Raport HTML",lambda:self.open_file("RAPORT.html")).pack(side="left")
        self.button(controls,"Kolorowy STEP",lambda:self.open_file("POROWNANIE_KOLORY.step")).pack(side="left",padx=8)
        self.button(controls,"Otwórz folder",self.open_folder).pack(side="right")
    def log_tab(self):
        tab=self.tabs["log"];self.txt(tab,"Dziennik analizy",16,FG,True).pack(anchor="w",pady=(0,12))
        self.console=tk.Text(tab,bg="#111b26",fg=FG,insertbackground=FG,font=("Consolas",10),
                             relief="flat",wrap="word",padx=12,pady=12);self.console.pack(fill="both",expand=True)
    def run(self):
        if self.busy:return
        try:
            a,b=Path(self.a.get()),Path(self.b.get())
            if not a.is_file() or not b.is_file():raise ValueError("Wskaż dwa istniejące pliki STEP")
            tol=float(self.tolerance.get().replace(",","."));rho=float(self.density.get().replace(",","."))
            if not 0<tol<=1 or not 0<rho<=25000:raise ValueError("Nieprawidłowa tolerancja lub gęstość")
        except Exception as e:messagebox.showerror("DS Compare",str(e));return
        self.busy=True;self.cancel_flag.clear();self.go.config(state="disabled");self.stop.config(state="normal")
        self.progress.start(12);self.console.delete("1.0","end")
        self.status.set("Trwa analiza B-Rep...")
        def work():
            try:
                folder,records,error=process(str(a),str(b),self.output.get(),tol,rho,self.save_step.get(),
                    progress=lambda s:self.q.put(("log",s)),cancelled=self.cancel_flag.is_set)
                self.q.put(("done",str(folder),error))
            except Exception:self.q.put(("error",traceback.format_exc()))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:
            while True:
                e=self.q.get_nowait()
                if e[0]=="log":
                    self.console.insert("end",e[1]+"\n");self.console.see("end");self.status.set(e[1])
                else:
                    self.busy=False;self.go.config(state="normal");self.stop.config(state="disabled");self.progress.stop()
                    if e[0]=="error":
                        self.status.set("Błąd porównania")
                        self.console.insert("end",e[1]+"\n");self.open_tab("log")
                        messagebox.showerror("DS Compare",e[1][-1600:])
                    else:
                        self.result=Path(e[1]);self.load_results()
                        self.status.set("Porównanie zakończone");self.open_tab("results")
                        if e[2]:messagebox.showwarning("STEP",str(e[2]))
        except queue.Empty:pass
        self.after(120,self.poll)
    def load_results(self):
        with (self.result/"PODSUMOWANIE.json").open(encoding="utf-8") as f:statuses=json.load(f).get("statuses",{})
        for key,label in self.numbers.items():
            n=statuses.get(key,0)
            if key=="SAME":n+=statuses.get("RENAMED",0)
            elif key=="CHANGED":n+=statuses.get("MOVED",0)+statuses.get("ADDED",0)
            label.config(text=str(n))
        for x in self.grid.get_children():self.grid.delete(x)
        with (self.result/"ZMIANY.csv").open(encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f,delimiter=";"):
                self.grid.insert("","end",values=(r.get("Status",""),r.get("Nazwa A",""),r.get("Nazwa B",""),r.get("Uwagi","")))
    def open_file(self,name):
        if not self.result:return messagebox.showinfo("DS Compare","Najpierw wykonaj porównanie")
        p=self.result/name
        if not p.exists():return messagebox.showwarning("DS Compare","Nie znaleziono "+name)
        if os.name=="nt":os.startfile(p)
        else:webbrowser.open(p.as_uri())
    def open_folder(self):
        p=self.result or Path(self.output.get());p.mkdir(parents=True,exist_ok=True)
        if os.name=="nt":os.startfile(p)
        else:webbrowser.open(p.as_uri())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--a",default="");parser.add_argument("--b",default="")
    args=parser.parse_args()
    App(args.a,args.b).mainloop()
if __name__=="__main__":main()
