"""RC9: preserve strict B-Rep matching; isolate optional revision material overlap.
A failed Common/Cut proof must never produce SAME/CHANGED. Preserve ADDED/REMOVED.
"""
from pathlib import Path
import ast
import sys

path=Path(sys.argv[1])
src=path.read_text(encoding="utf-8")
def patch(old,new,expected=1):
    global src
    n=src.count(old)
    if n!=expected:
        raise SystemExit(f"RC9 patch mismatch: expected {expected}, got {n}: {old[:100]!r}")
    src=src.replace(old,new)

patch("budget_exceeded=False,min_common_larger_same_name",
      "budget_exceeded=False,native_failures=0,native_failure_examples=[],\\n              min_common_larger_same_name".replace("\\n","\n"))
patch("    guarded_budget_s=240.0\n","    guarded_budget_s=240.0\n    guarded_deadline_hit=False\n")
patch("            stat['boolean_checks']+=1\n",
      "            if perf_counter()-guarded_started>=guarded_budget_s:\n                guarded_deadline_hit=True\n                break\n            stat['boolean_checks']+=1\n")
patch("                    if perf_counter()-guarded_started>=guarded_budget_s:\n                        raise NativeGeometryFailure('Limit czasu bezpiecznej analizy wspólnego materiału — nieukończone porównanie')\n","")
patch("            except NativeGeometryFailure:\n                raise\n            except Exception:\n                stat['invalid_boolean']+=1;continue\n",
      """            except NativeGeometryFailure as exc:
                # Optional Common failed. Keep original ADDED/REMOVED, never infer SAME.
                stat['invalid_boolean']+=1
                stat['native_failures']+=1
                if len(stat['native_failure_examples'])<12:
                    stat['native_failure_examples'].append(dict(a_index=i,b_index=j,error=str(exc)))
                trace.mark('revision_overlap_guard','OPTIONAL_COMMON_FAILED',a_id=i,b_id=j,error=str(exc))
                continue
            except Exception:
                stat['invalid_boolean']+=1;continue
""")
patch("        if stat['budget_exceeded']:raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')\n",
      """        if stat['budget_exceeded'] or guarded_deadline_hit:
            # No optional Boolean proof: preserve unmatched ADDED/REMOVED records.
            stat['budget_exceeded']=True
            trace.mark('revision_overlap_guard','OPTIONAL_BUDGET_EXCEEDED',checks=stat['boolean_checks'])
            break
""")
patch("        except NativeGeometryFailure:\n            raise\n        except Exception:\n            stat['invalid_boolean']+=1;continue\n",
      """        except NativeGeometryFailure as exc:
            stat['invalid_boolean']+=1
            stat['native_failures']+=1
            if len(stat['native_failure_examples'])<12:
                stat['native_failure_examples'].append(dict(a_index=i,b_index=j,stage='material_regions',error=str(exc)))
            trace.mark('revision_overlap_guard','OPTIONAL_REGIONS_FAILED',a_id=i,b_id=j,error=str(exc))
            continue
        except Exception:
            stat['invalid_boolean']+=1;continue
""")
ast.parse(src)
path.write_text(src,encoding="utf-8")
print("Patched RC9 optional material overlap; B-Rep equality/tolerance unchanged")
