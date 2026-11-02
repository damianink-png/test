"""Update frozen Qt regression assertions to the explicitly requested UI.

Keep all geometry, report completeness, settings, color and export tests.
Only remove assumptions that the user-rejected details table and blocking
partial-report dialog must be visible.
"""
from pathlib import Path
import sys

p=Path(sys.argv[1])/"tests"/"test_ui_polish.py"
s=p.read_text(encoding="utf-8")
def replace(old,new):
    global s
    if s.count(old)!=1:
        raise RuntimeError(f"Legacy UI regression patch anchor mismatch: {old[:100]!r}, count={s.count(old)}")
    s=s.replace(old,new)

replace(
"""    assert w._details_toggle.isVisible()
    w._details_toggle.click();assert w.compare_table.rowCount()==2 and w._details.isVisible()
    w.filter_selector.setCurrentIndex(w.filter_selector.findData('CHANGED'))
    assert w.compare_table.isRowHidden(0) and not w.compare_table.isRowHidden(1)
    w.select_filter('ALL');w.search.setText('nowa')
    assert w.compare_table.isRowHidden(0) and not w.compare_table.isRowHidden(1)""",
"""    # User removed the detail table and search/filter controls from the UI.
    assert w._details_toggle.isHidden() and w._details.isHidden()
    assert w.reset_button.isVisible()
    assert w.run_compare.text()=='Porównaj rewizje'""")
start=s.index("@pytest.mark.parametrize('choose_review',[False,True])")
end=s.index("def test_partial_result_is_labeled_and_all_unknown_rows_remain_visible",start)
if s.count("@pytest.mark.parametrize('choose_review',[False,True])")!=1:
    raise RuntimeError("Unexpected old partial modal tests")
s=s[:start]+"""def test_partial_report_is_automatically_approved_without_modal(win,tmp_path):
    import json
    from PySide6.QtCore import QProcess
    w=win;w.task='compare';w.current_folder=tmp_path;w.active_log=w.log
    w.process=QProcess(w);w.was_cancelled=False
    (tmp_path/'_WYROWNANIE_PYTANIE.json').write_text(json.dumps({
        'token':'material-choice','material_unverified':True,'unverified_A':31,'unverified_B':31,
        'reason':'source tolerance 0.17 mm > 0.01 mm'}))
    w._coordinate_prompt()
    reply=json.loads((tmp_path/'_WYROWNANIE_ODPOWIEDZ.json').read_text())
    assert reply=={'token':'material-choice','decision':'review'}
    assert not w.was_cancelled
    assert QApplication.activeModalWidget() is None
    w.process=None


"""+s[end:]
replace(
"""    w._details_toggle.click();assert w.compare_table.rowCount()==3""",
"""    assert w._details_toggle.isHidden() and w._details.isHidden()
    assert (folder/'ZMIANY.csv').exists()""")
p.write_text(s,encoding="utf-8")
print("DSCOMPARE_LEGACY_UI_REGRESSIONS_UPDATED_PASS",p,flush=True)
