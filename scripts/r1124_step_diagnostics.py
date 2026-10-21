"""DS Compare R11.24: auditable STEP assembly diagnostics.

This module intentionally does not remove XCAF assembly parents. A parent
without its own solid is not an empty physical part: deleting it can destroy
the assembly hierarchy. Diagnostic totals are independent of product names.
"""
from __future__ import annotations
from pathlib import Path
import json
import re
from datetime import datetime,timezone

_PRODUCT=re.compile(rb"(?m)^#\d+\s*=\s*PRODUCT\('((?:[^']|'')*)'")
_USAGE=re.compile(rb"(?m)^#\d+\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\(")
_ABSR_BREP=re.compile(rb"(?m)^#\d+\s*=\s*ADVANCED_BREP_SHAPE_REPRESENTATION\(")
_SHELL=re.compile(rb"(?m)^#\d+\s*=\s*CLOSED_SHELL\(")
_SOLID=re.compile(rb"(?m)^#\d+\s*=\s*MANIFOLD_SOLID_BREP\(")
_COMPONENT=re.compile(rb"(?m)^#\d+\s*=\s*PRODUCT_DEFINITION_SHAPE\(")
_STATUS=("BEZ_ZMIAN","PRZESUNIETE","NOWE","USUNIETE","ZMIENIONE")

def inspect(path, export_info=None, omitted_geometry=None):
    file=Path(path)
    data=file.read_bytes()
    products=[p.decode("utf-8","replace").replace("''","'") for p in _PRODUCT.findall(data)]
    n_usage=len(_USAGE.findall(data))
    n_solids=len(_SOLID.findall(data))
    info=dict(export_info or {})
    actual=info.get("rzeczywiste_bryly_step")
    if not isinstance(actual,int) or isinstance(actual,bool):
        actual=info.get("liczba_bryl") if isinstance(info.get("liczba_bryl"),int) else None
    candidates=[p for p in products if p.upper().startswith("ABSR")]
    result={
       "format":"DSCOMPARE_STEP_DIAG_V2",
       "data_utc":datetime.now(timezone.utc).isoformat(),
       "plik":file.name,
       "rozmiar_bajty":len(data),
       "liczba_produktow_step":len(products),
       "liczba_polaczen_podzlozen":n_usage,
       "produkty_z_nazwa_absr":candidates,
       "wystapienia_advanced_brep_shape_representation":len(_ABSR_BREP.findall(data)),
       "wystapienia_manifold_solid_brep":n_solids,
       "wystapienia_closed_shell":len(_SHELL.findall(data)),
       "produkty":products,
       "produkty_techniczne_ponad_bryly":(
          max(0,len(products)-actual) if actual is not None else None
       ),
       "realne_bryly_w_raporcie":actual,
       "grupy_statusow":[p for p in products if any(k in p.upper() for k in _STATUS)],
       "pominięta_geometria":omitted_geometry or {},
       "uwaga":"Kontenery STEP reprezentują złożenia i mogą mieć zerową własną masę. Nie są pustymi bryłami. ZW3D może nazywać kontenery ABSR; konieczna kontrola importu.",
       "eksporter":info,
    }
    return result

def save(path,export_info=None,omitted_geometry=None):
    source=Path(path)
    report=source.with_name(source.stem+"_DIAGNOSTYKA_STEP.json")
    report.write_text(json.dumps(inspect(source,export_info,omitted_geometry),
                                 ensure_ascii=False,indent=2,default=str),encoding="utf8")
    return str(report)
