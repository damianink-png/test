"""R11.26 - remove settings self-test UI and on-page mass results grid.

Preserves the R11.25 CAD comparison/ABSR engine and the mass report generator.
Hidden table widget stays as a data adapter used by existing report/Qt handlers,
but is not part of the page layout and never shown in the application.
"""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text('utf8')
settings_a=s.index(" def _modern_settings(self):")
settings_b=s.index(" def create_zw3d_macro(self):",settings_a)
settings=s[settings_a:settings_b]

start=settings.index("  testbox,tp=self._settings_card('Testy')")
end=settings.index("  for form in (cp,rp,tp):",start)
settings=settings[:start]+settings[end:]
for old,new in [
    ("  for form in (cp,rp,tp):","  for form in (cp,rp):"),
    ("  grid.addWidget(testbox,1,0,1,2)\n",""),
    ("  self.test_process=None;self.test_report=None\n","")
]:
    count=settings.count(old)
    if count!=1:raise RuntimeError(f"R11.26 settings anchor {old[:70]!r} count={count}")
    settings=settings.replace(old,new,1)
# Delete obsolete slot implementations (no UI controls invoke them).
slots=settings.index(" def _run_local_tests(self):")
settings=settings[:slots]
assert 'Testy' not in settings and 'test_run' not in settings
s=s[:settings_a]+settings+s[settings_b:]

# The internal mass table is used by report compatibility functions. Remove
# its PANEL from the mass page rather than detaching the data model itself.
old="""  md.addWidget(self.mass_table);self._mass_details.setMinimumHeight(310)
  lay.addWidget(self._mass_details,1);self._mass_details.hide()"""
new="""  md.addWidget(self.mass_table)
  # No mass results table in the application. Full parts list remains in the
  # generated HTML report, accessible through its existing action buttons.
  self._mass_details.hide()"""
assert s.count(old)==1, ("mass panel anchor",s.count(old))
s=s.replace(old,new,1)
# Remove the R11.25 post-load show; keep result file/report buttons active.
old="""   self._refresh_mass_summary(folder)
   self._format_mass_results()
   self._mass_details.show()"""
new="""   self._refresh_mass_summary(folder)
   self._format_mass_results()"""
assert s.count(old)==1, ("mass load anchor",s.count(old))
s=s.replace(old,new,1)
# Safety: verify no code elsewhere could expose the old mass table panel.
if '_mass_details.show()' in s or "lay.addWidget(self._mass_details" in s:
    raise RuntimeError("R11.26 found an alternate path revealing mass results table")
p.write_text(s,encoding='utf8')
(root/'VERSION.txt').write_text('R11.26\n',encoding='utf8')
meta=root/'build_info.json'
if meta.is_file():
    d=json.loads(meta.read_text('utf8'))
    d['version']='R11.26 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
    d['ui']='No Testy settings section; no on-page mass results table; mass actions and report preserved'
    meta.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('R11.26: settings tests removed, mass grid removed, output buttons untouched; STEP/ABSR engine unchanged')
