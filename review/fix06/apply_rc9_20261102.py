"""Apply verified RC9 fixes to the pinned source snapshot before Windows build.
Refuse to build when the upstream layout differs unexpectedly.
"""
from pathlib import Path
import sys, compileall
root=Path(sys.argv[1]).resolve()
def change(file,old,new,marker=None):
    p=root/"dsac29"/file
    s=p.read_text(encoding="utf-8")
    if old not in s:
        if marker and marker in s:return
        raise RuntimeError(f"Missing source pattern in {p}: {old[:70]!r}")
    if s.count(old)!=1:raise RuntimeError(f"Ambiguous source pattern in {p}")
    p.write_text(s.replace(old,new),encoding="utf-8")

change("revision_overlap.py",
    "    if review_approval(proposal)!='review':\n        raise InterruptedError('Anulowano przygotowanie raportu częściowego.')",
    "    # Automatically save partial output; unresolved pairs remain UNCERTAIN.\n    trace.mark('revision_overlap_guard','AUTO_PARTIAL',reason=proposal['reason'])",
    "trace.mark('revision_overlap_guard','AUTO_PARTIAL'")
change("revision_overlap.py",
    "        pending=[f for f in failures if f['error'].startswith('Nie wykonano testu:')]\n        for failure in pending[:16]:\n            if perf_counter()-retry_started>=60.0:break",
    "        # Prioritize failed geometry over pairs skipped due to global budget.\n        pending=sorted(failures,key=lambda f:f['error'].startswith('Nie wykonano testu:'))\n        for failure in pending[:20]:\n            if perf_counter()-retry_started>=120.0:break",
    "pending=sorted(failures,key=lambda f:f['error'].startswith('Nie wykonano testu:'))")
change("revision_overlap.py",
    "                reg=trace.brep_call('revision_budget_retry_regions',i,j,calculate,a[i],b[j],tolerance)",
    """                from .native_guard import guarded_common
                try:
                    common_shape=trace.brep_call('revision_isolated_retry_common',i,j,guarded_common,
                                                 a[i].shape,b[j].shape,tolerance)
                    common_shape=bind_common(common_shape,a[i].shape,b[j].shape,tolerance)
                except (NativeGeometryFailure,ValueError,RuntimeError,OSError) as common_exc:
                    common_shape=None
                    trace.mark('revision_isolated_retry_common','FALLBACK_REGIONS',
                               a_index=i,b_index=j,error=str(common_exc))
                try:
                    reg=trace.brep_call('revision_isolated_retry_regions',i,j,calculate,
                                        a[i],b[j],tolerance,common_shape=common_shape)
                except (NativeGeometryFailure,ValueError,RuntimeError,OSError):
                    if common_shape is None:raise
                    reg=trace.brep_call('revision_isolated_retry_regions_uncached',i,j,calculate,
                                        a[i],b[j],tolerance)""",
    "'revision_isolated_retry_regions_uncached'")
change("revision_overlap.py",
    "                stat['retry_budget_recovered']+=1",
    "                stat['retry_budget_recovered']+=1\n                trace.mark('revision_isolated_retry','RECOVERED',a_index=i,b_index=j,decision=proof.decision)",
    "trace.mark('revision_isolated_retry','RECOVERED'")
p=root/"dsac29"/"gui45.py"
s=p.read_text(encoding="utf-8")
start="            box=QMessageBox(self);box.setWindowTitle('Niepełna analiza geometrii')"
end="            return\n        delta=data.get("
if start in s:
    a=s.index(start);b=s.index(end,a)
    s=s[:a]+"""            self.active_log.appendPlainText('Raport częściowy: niepotwierdzone elementy pozostaną do sprawdzenia.')
            self._reply_coordinate_prompt(token,'review')
"""+s[b:]
    p.write_text(s,encoding="utf-8")
elif "self._reply_coordinate_prompt(token,'review')" not in s:raise RuntimeError("gui45 layout changed")
change("gui46.py",
    "  runline.addWidget(self.compare_summary,1);lay.addLayout(runline)",
    "  runline.addWidget(self.compare_summary,1);lay.addLayout(runline)\n  self.reset_button=button('Nowe porównanie',self.reset_session)\n  lay.addWidget(self.reset_button,0,Qt.AlignLeft)",
    "lay.addWidget(self.reset_button,0,Qt.AlignLeft)")
change("gui46.py",
    "  toolrow.addWidget(self.filter_selector);lay.addLayout(toolrow)",
    "  toolrow.addWidget(self.filter_selector);lay.addLayout(toolrow)\n  for _widget in (heading,self.search,self.filter_selector):_widget.hide()",
    "for _widget in (heading,self.search,self.filter_selector):_widget.hide()")
change("gui46.py",
    "  lay.addWidget(self.compare_table,1)",
    "  lay.addWidget(self.compare_table,0)\n  self.compare_table.hide()",
    "self.compare_table.hide()")
change("gui46.py",
    "  foot=QHBoxLayout();foot.addStretch()\n  self.reset_button=button('Nowe porównanie',self.reset_session)\n  foot.addWidget(self.reset_button);lay.addLayout(foot)",
    "",
    "lay.addWidget(self.reset_button,0,Qt.AlignLeft)")
# CLI/worker must not require the old --allow-review-decision flag to
# save verified results and mark unverified geometry UNCERTAIN.
change("cli.py",
    "review_approval=material_approval,geometry_context=geometry_context)",
    "review_approval=material_approval or (lambda _proposal:'review'),geometry_context=geometry_context)",
    "review_approval=material_approval or (lambda _proposal:'review')")
assert compileall.compile_dir(str(root/"dsac29"),quiet=1)
print("PATCHED_AND_COMPILED",root)
