"""Run the exact uploaded Trident R1/R2 pair using the current DS Compare CAD engine."""
from __future__ import annotations
import argparse
import faulthandler
import json
import os
import sys
import time
import traceback
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--a",type=Path,required=True)
    ap.add_argument("--b",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("evidence/exact_comparison"))
    ap.add_argument("--log",type=Path,default=Path("evidence/exact_progress.log"))
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    args.log.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    with (args.log.parent/"native_watchdog_stack.log").open("w",encoding="utf-8",buffering=1) as watchdog:
        faulthandler.enable(file=watchdog,all_threads=True)
        faulthandler.dump_traceback_later(300,repeat=True,file=watchdog)
        def progress(message):
            stamp=round(time.monotonic()-started,3)
            line=f"{stamp}s {message}"
            print(line,flush=True)
            with args.log.open("a",encoding="utf-8") as stream:
                stream.write(line+"\n")
                stream.flush()
                os.fsync(stream.fileno())
        try:
            from trident_exact_audit import preflight
            proof=preflight(args.a,args.b)
            progress("EXACT_INPUT_SHA256_VERIFIED "+json.dumps(proof))
            from dsac29.cli import process
            folder,records,export_error=process(
                str(args.a),str(args.b),str(args.out),
                tolerance=0.01,density=7850.0,step=True,
                preview3d=True,revision_style=True,
                full_bom=False,bom_csv=False,diff_step=True,
                auto_align=False,force_unrelated=True,
                progress=progress)
            counts={status:sum(x.status==status for x in records) for status in
                    ("SAME","RENAMED","CHANGED","MOVED","ADDED","REMOVED","UNCERTAIN")}
            result={"status":"FINISHED","elapsed_s":round(time.monotonic()-started,3),
                    "counts":counts,"step_export_error":export_error,
                    "output":str(folder),"engine":"review/fix06/dsac29"}
            (args.log.parent/"exact_execution.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
            progress("EXACT_COMPARISON_FINISHED "+json.dumps(result))
            return 0 if export_error is None else 2
        except BaseException as exc:
            result={"status":"FAILED","elapsed_s":round(time.monotonic()-started,3),
                    "exception":repr(exc),"traceback":traceback.format_exc()}
            (args.log.parent/"exact_execution.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
            progress("EXACT_COMPARISON_FAILED "+repr(exc))
            traceback.print_exc()
            return 1
        finally:
            faulthandler.cancel_dump_traceback_later()

if __name__=="__main__":
    raise SystemExit(main())
