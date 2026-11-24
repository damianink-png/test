"""Publish a marked partial mass report if some solids cannot be measured."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) / 'dsac29'
p = root / 'single_mass.py'
source = p.read_text(encoding='utf-8')
source = source.replace('diagnostics=import_stats,max_solids=max_solids)',
                        'diagnostics=import_stats,max_solids=max_solids,partial_mass=True)')
source = source.replace("    summary = {", """    omitted_solids=import_stats.get('invalid_mass_solids',[])
    complete=not omitted_solids and not import_stats.get('faces_outside_solids')
    summary = {'analysis_complete':complete,'invalid_mass_solid_count':len(omitted_solids),""")
source = source.replace('    from .report_view import enhance_mass_report', '''    details_path=folder/'POMINIETE_BRYLY_MASY.json'
    if omitted_solids:
        warning=f"Wynik częściowy. Obliczono masę wczytanych brył. Pominięte bryły: {len(omitted_solids)}."
        details_path.write_text(json.dumps(omitted_solids, ensure_ascii=False, indent=2), encoding='utf-8')
        page=page.replace('<body>','<body><p role="alert">'+html.escape(warning)
                          +' <a href="POMINIETE_BRYLY_MASY.json">Lista brył i przyczyny</a></p>',1)
        if progress:progress(warning)
    else:
        details_path.unlink(missing_ok=True)
    from .report_view import enhance_mass_report''')
assert 'partial_mass=True' in source and 'details_path=' in source
p.write_text(source, encoding='utf-8')

p = root / 'mass_batch.py'
source = p.read_text(encoding='utf-8')
source = source.replace("            'pominięte_powierzchnie':", """            'analysis_complete':data['analysis_complete'],
            'invalid_mass_solid_count':data['invalid_mass_solid_count'],
            'pominięte_powierzchnie':""")
source = source.replace("    summary={'plik':", """    skipped=sum(entry['invalid_mass_solid_count'] for entry in entries)
    complete=all(entry['analysis_complete'] for entry in entries)
    summary={'analysis_complete':complete,'invalid_mass_solid_count':skipped,'plik':""")
source = source.replace('    from .report_view import enhance_mass_report', '''    if not complete:
        warning=(f'Wynik częściowy. Suma obejmuje wczytane bryły. '
                 f'Pominięte bryły: {skipped}. Szczegóły w raportach modeli.')
        report=report.replace('<body>','<body><p role="alert">'+html.escape(warning)+'</p>',1)
        if progress:progress(warning)
    from .report_view import enhance_mass_report''')
assert "'analysis_complete':complete" in source and 'if not complete:' in source
p.write_text(source, encoding='utf-8')
