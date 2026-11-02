"""Fetch byte-identical public Voron STEP archives; never accept another revision."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path
from trident_exact_audit import SOURCES

ARCHIVES={
    "Trident_Assembly1.step":{
        "url":"https://raw.githubusercontent.com/VoronDesign/Voron-Trident/cc1d765173c12e9a7b6a1f14f6f213ef8bfb1b04/CAD/Trident_Assembly_STEP.zip",
        "entry":"Trident_Assembly.step",
        "revision":"Voron-Trident R1 2025-06-15",
    },
    "trident_assembly.step":{
        "url":"https://raw.githubusercontent.com/VoronDesign/Voron-Trident/1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a/CAD/trident_assembly.step.zip",
        "entry":"trident_assembly.step",
        "revision":"Voron-Trident R2 2026-06-25",
    },
}

def fetch(out: Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    evidence={}
    for name,origin in ARCHIVES.items():
        target=out/name
        temporary=out/(name+".partial")
        archive=out/(name+".source.zip")
        try:
            with urllib.request.urlopen(origin["url"],timeout=120) as response, archive.open("wb") as f:
                shutil.copyfileobj(response,f,length=4*1024*1024)
            with zipfile.ZipFile(archive) as z:
                if origin["entry"] not in z.namelist():
                    raise RuntimeError("Expected STEP ZIP member missing: "+origin["entry"])
                h=hashlib.sha256()
                size=0
                with z.open(origin["entry"]) as inp, temporary.open("wb") as dst:
                    while block:=inp.read(4*1024*1024):
                        h.update(block);dst.write(block);size+=len(block)
            expected=SOURCES[name]
            if size!=expected["bytes"] or h.hexdigest()!=expected["sha256"]:
                raise RuntimeError(f"NOT EXACT: {name}: {size} bytes SHA256 {h.hexdigest()}")
            temporary.replace(target)
            evidence[name]={"verified":True,"bytes":size,"sha256":h.hexdigest(),**origin}
        finally:
            temporary.unlink(missing_ok=True)
            archive.unlink(missing_ok=True)
    (out/"EXACT_INPUT_PROVENANCE.json").write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding="utf-8")
    return evidence

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=Path("models/user_exact"))
    args=ap.parse_args()
    print(json.dumps(fetch(args.out),indent=2,ensure_ascii=False))
