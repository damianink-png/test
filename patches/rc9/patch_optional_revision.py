"""Fail closed on optional revision Common/Cut failure: keep ADDED/REMOVED.
Does not alter B-Rep equality proof or tolerance.
"""
from pathlib import Path
import ast,sys
p=Path(sys.argv[1]);s=p.read_text(encoding="utf-8")
def sub(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError("Unexpected RC9 source: "+repr(old[:80]))
 s=s.replace(old,new)
sub("budget_exceeded=False,min_common_larger_same_name=",
    "budget_exceeded=False,native_failures=0,native_failure_examples=[],min_common_larger_same_name=")
sub("    guarded_budget_s=240.0\n","    guarded_budget_s=240.0\n    guarded_deadline_hit=False\n")
sub("            stat['boolean_checks']+=1\n",
    "            if perf_counter()-guarded_started>=guarded_budget_s:\n                guarded_deadline_hit=True\n                break\n            stat['boolean_checks']+=1\n")
sub("                    if perf_counter()-guarded_started>=guarded_budget_s:\n                        raise NativeGeometryFailure('Limit czasu bezpiecznej analizy wspólnego materiału — nieukończone porównanie')\n","")
sub("            except NativeGeometryFailure:\n                raise\n            except Exception as exc:\n                raise NativeGeometryFailure('Niekompletna analiza wspólnego materiału: '+str(exc)) from exc\n",
"""            except Exception as exc:
                stat['invalid_boolean']+=1
                stat['native_failures']+=1
                if len(stat['native_failure_examples'])<12:
                    stat['native_failure_examples'].append(dict(a_index=i,b_index=j,stage='common',error=str(exc)))
                trace.mark('revision_overlap_guard','OPTIONAL_COMMON_FAILED',a_id=i,b_id=j,error=str(exc))
                continue
""")
sub("        if stat['budget_exceeded']:raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')\n",
"""        if stat['budget_exceeded'] or guarded_deadline_hit:
            stat['budget_exceeded']=True
            trace.mark('revision_overlap_guard','OPTIONAL_BUDGET_EXCEEDED',checks=stat['boolean_checks'])
            break
""")
sub("        except NativeGeometryFailure:\n            raise\n        except Exception as exc:\n            raise NativeGeometryFailure('Niekompletna analiza różnic materiału: '+str(exc)) from exc\n",
"""        except Exception as exc:
            stat['invalid_boolean']+=1
            stat['native_failures']+=1
            if len(stat['native_failure_examples'])<12:
                stat['native_failure_examples'].append(dict(a_index=i,b_index=j,stage='material_regions',error=str(exc)))
            trace.mark('revision_overlap_guard','OPTIONAL_REGIONS_FAILED',a_id=i,b_id=j,error=str(exc))
            continue
""")
ast.parse(s);p.write_text(s,encoding="utf-8")
if len(sys.argv)>2:
 t=Path(sys.argv[2]);z=t.read_text(encoding="utf-8")
 old="    with pytest.raises(NativeGeometryFailure):\n        merge_material_revisions([a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')])"
 new="""    records,regions,diagnostics=merge_material_revisions(
        [a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')])
    assert sorted(r.status for r in records)==['ADDED','REMOVED']
    assert not regions
    assert diagnostics['native_failures']==1
    assert diagnostics['native_failure_examples'][0]['stage']=='common'
    assert diagnostics['accepted']==0"""
 if z.count(old)!=1:raise RuntimeError("Unexpected stability regression")
 z=z.replace(old,new);ast.parse(z);t.write_text(z,encoding="utf-8")
print("RC9 optional Common/Cut fails closed to ADDED/REMOVED; tolerance unchanged")
