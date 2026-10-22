"""R11.25 local, synthetic, confidential-safe STEP diagnostics.

Only synthetic rectangular solids are used; the report contains counts and
flags rather than part names, user paths, or source geometry. No network.
"""
from pathlib import Path
from time import perf_counter
from datetime import datetime
import json,traceback
import re

NAME="TESTY_DS_COMPARE_R1125.txt"
STEPS=(("STANDARDOWY","STEP_STANDARD.step"),("BEZ_KORZENIA","STEP_GRUPY_BEZ_KORZENIA.step"),("PLASKI","STEP_PLASKI.step"))

def run(folder, progress=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    say=progress or (lambda message:None)
    lines=[
        "DS COMPARE R11.25 - DIAGNOSTYKA LOKALNA",
        "Data lokalna: "+datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Prywatnosc: wylacznie syntetyczne prostopadlosciany; zadnych firmowych STEP, nazw czesci ani sciezek.",
        "NIE jest to test importera ZW3D 2019. Wynik importu nalezy uzupelnic ponizej.",
        "",
        "[AUTOMATYCZNE TESTY]",
    ]
    outcomes={}
    def check(key, callback):
        started=perf_counter()
        try:
            detail=callback()
            outcomes[key]={"ok":True,"details":detail,"sec":round(perf_counter()-started,3)}
            say("PASS: "+key)
        except Exception as exc:
            outcomes[key]={"ok":False,"details":type(exc).__name__,"sec":round(perf_counter()-started,3)}
            # Full developer exception retained only locally in a second file.
            with (folder/"TESTY_LOKALNE_BLEDY.txt").open("a",encoding="utf8") as f:
                f.write("FAIL "+key+"\n"+traceback.format_exc()+"\n")
            say("FAIL: "+key+" ("+type(exc).__name__+")")
    ctx={}
    def prepare():
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Trsf,gp_Vec
        from OCP.TopLoc import TopLoc_Location
        from dsac29.geometry import describe
        from dsac29.compare import compare
        from dsac29.revision_rules import classify_revisions
        from dsac29.geometry_registry import GeometryRegistry
        def box(name,x,y,length):
            solid=BRepPrimAPI_MakeBox(length,11,9).Shape()
            tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(x),float(y),0))
            return describe(solid.Located(TopLoc_Location(tr)),name,name)
        a=[box('T_SAME',0,0,19),box('T_MOVE',40,0,17),box('T_REMOVED',85,0,23)]
        b=[box('T_SAME',0,0,19),box('T_MOVE',40,39,17),box('T_ADDED',155,0,29)]
        geo=GeometryRegistry()
        rows=compare(a,b,revision_only=True,geometry_context=geo)
        rows=classify_revisions(a,b,rows,0.01,geometry_context=geo)
        states={r.status for r in rows}
        expected={'SAME','MOVED','REMOVED','ADDED'}
        if not expected.issubset(states):
            raise AssertionError("Brakuje statusow w probce")
        ctx.update(a=a,b=b,rows=rows)
        return "Zgodnosc / przesuniecie / usuniecie / dodanie: 4 statusy rozpoznane"
    check("Geometria i wykrywanie 4 statusow",prepare)

    def moved_parity():
        from dsac29.compare import compare
        from dsac29.revision_rules import classify_revisions
        from dsac29.geometry_registry import GeometryRegistry
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Trsf,gp_Vec
        from OCP.TopLoc import TopLoc_Location
        from dsac29.geometry import describe
        def one(x):
            tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(x),0,0))
            return describe(BRepPrimAPI_MakeBox(21,12,8).Shape().Located(TopLoc_Location(tr)),'T_MANY','T_MANY')
        def compare_status(a,b):
            geo=GeometryRegistry()
            rec=compare(a,b,revision_only=True,geometry_context=geo)
            return classify_revisions(a,b,rec,0.01,geometry_context=geo)
        same=compare_status([one(0)],[one(55)])
        different=compare_status([one(0)],[one(55),one(105)])
        if [r.status for r in same]!=['MOVED']:raise AssertionError("Bledne przesuniecie 1:1")
        if any(r.status=='MOVED' for r in different) or len(different)!=3:
            raise AssertionError("Bledna kategoria po zmianie liczby wystapien")
        return "MOVED 1:1; przy 1:2 tylko ADDED/REMOVED"
    check("Rozna liczba wystapien",moved_parity)

    def export_variant(label,name,flat,rootless):
        from dsac29.step_io import _export_revision_step,inspect_step_colors
        from dsac29.step_diagnostics import inspect
        path=folder/name
        t=perf_counter()
        output=_export_revision_step(str(path),ctx['rows'],ctx['a'],ctx['b'],progress=None,
                    reuse_definitions=False,flat_zw3d=flat,rootless_group=rootless)
        elapsed=round(perf_counter()-t,3)
        stats=inspect(path,output)
        imported=inspect_step_colors(str(path))
        real=imported['bryly_wynikowe']
        if real<4 or imported['elementy_bez_bryly'] or imported['bryly_bez_koloru'] or imported['powierzchnie_bez_koloru']:
            raise AssertionError("Niekompletne bryly lub kolory")
        if bool(stats['liczba_polaczen_podzlozen'])==flat:raise AssertionError("Niepoprawna struktura zlozenia")
        if flat and stats['liczba_produktow_step']!=real:raise AssertionError("Plaski STEP zawiera dodatkowe produkty")
        ctx[label]=dict(path=path,count=real,products=stats['liczba_produktow_step'],
                        usages=stats['liczba_polaczen_podzlozen'],seconds=elapsed,
                        solidbreps=stats['wystapienia_manifold_solid_brep'])
        return ("bryly={}; produkty={}; powiazania={}; zapis_s={}".format(
            real,stats['liczba_produktow_step'],stats['liczba_polaczen_podzlozen'],elapsed))
    for label,name in STEPS:
        check("Eksport "+label,lambda label=label,name=name:export_variant(label,name,
                                           flat=(label=="PLASKI"),rootless=(label=="BEZ_KORZENIA")))
    def crosscheck():
        std=ctx["STANDARDOWY"];root=ctx["BEZ_KORZENIA"];flat=ctx["PLASKI"]
        if len({std['count'],root['count'],flat['count']})!=1:
            raise AssertionError("Liczby bryl rozne")
        if root['products']!=std['products']-1:
            raise AssertionError("Brak oczekiwanej redukcji kontenera korzenia")
        if root['usages']>=std['usages'] or flat['usages']!=0:
            raise AssertionError("Niezgodne powiazania")
        return "Liczba bryl identyczna; bez korzenia o 1 produkt mniej; plaski bez powiazan"
    check("Porownanie 3 struktur STEP",crosscheck)

    def reimport():
        from dsac29.step_io import load_step
        first=ctx['STANDARDOWY']['path']
        t=perf_counter();a=load_step(str(first),max_solids=2000);cold=round(perf_counter()-t,3)
        t=perf_counter();b=load_step(str(first),max_solids=2000);warm=round(perf_counter()-t,3)
        if len(a)!=len(b) or not a or len(a)!=ctx["STANDARDOWY"]['count']:
            raise AssertionError("Rozna liczba bryl po ponownym imporcie")
        return f"Zapis ponownego odczytu: pierwszy={cold}s, drugi={warm}s, bryly={len(a)} (to nie test cache GUI)"
    check("Ponowny odczyt syntetycznego STEP",reimport)
    check("Schemat danych diagnostycznych",lambda:verify_diagnostics(ctx))
    total=sum(v['ok'] for v in outcomes.values())
    for name,result in outcomes.items():
        lines.append(("PASS" if result['ok'] else "FAIL")+" | "+name+" | "+result['details']+
                     " | "+str(result['sec'])+" s")
    lines += ["",f"WYNIK: {total}/{len(outcomes)} testow PASS",
        "", "[TEST IMPORTU DO ZW3D 2019 - WPISZ W PROGRAMIE]",
        "Standardowy: ABSR=nie sprawdzono; podzlozenia=nie sprawdzono",
        "Bez korzenia: ABSR=nie sprawdzono; podzlozenia=nie sprawdzono",
        "Plaski: ABSR=nie sprawdzono; podzlozenia=nie sprawdzono",
        "Uwaga: nie wysylaj plikow STEP; plik TXT zawiera tylko zagregowane wyniki syntetyczne.",
        "", "KONIEC DIAGNOSTYKI"]
    file=folder/NAME
    file.write_text("\n".join(lines)+"\n",encoding="utf8")
    say("Zapisano lokalny raport TXT (bez geometrii i nazw firmowych).")
    return dict(ok=total==len(outcomes),passed=total,total=len(outcomes),report=str(file),
                filenames=[x[1] for x in STEPS])

def verify_diagnostics(ctx):
    from dsac29.step_diagnostics import inspect
    for label,_ in STEPS:
        info=inspect(ctx[label]['path'])
        if not isinstance(info['wystapienia_manifold_solid_brep'],int):
            raise AssertionError("Brak licznika BRep")
    return "Sprawdzono strukture diagnostyki STEP dla 3 wariantow"

def update_zw3d_results(report,observations):
    """Replace only fixed synthetic ZW3D rows, never append model paths/names."""
    report=Path(report)
    if report.name!=NAME or not report.is_file():
        raise ValueError("Najpierw uruchom testy lokalne")
    text=report.read_text('utf8')
    labels={"STANDARDOWY":"Standardowy","BEZ_KORZENIA":"Bez korzenia","PLASKI":"Plaski"}
    for key,caption in labels.items():
        v=observations.get(key,{})
        count=v.get("absr",-1)
        if not isinstance(count,int) or not -1<=count<=100000:raise ValueError("Liczba ABSR poza zakresem")
        group=v.get("groups","Nie sprawdzono")
        if group not in ("Nie sprawdzono","Tak","Nie","Czesciowo"):raise ValueError("Niepoprawny status podzlozen")
        replacement=f"{caption}: ABSR={count if count>=0 else 'nie sprawdzono'}; podzlozenia={group.lower()}"
        pattern=re.compile(r"^"+re.escape(caption)+r": ABSR=.*$",re.MULTILINE)
        new,n=pattern.subn(replacement,text)
        if n!=1:raise ValueError("Nie znaleziono wiersza: "+caption)
        text=new
    report.write_text(text,encoding="utf8")
    return str(report)
