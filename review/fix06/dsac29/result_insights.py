"""Presentation metadata built from existing evidence; never assigns CAD verdicts."""
from html import escape


def enriched_records(records, a, b, overlap=None, material_errors=None):
    overlap = overlap or {}
    errors = material_errors or {}
    result = []
    for index, record in enumerate(records):
        row = {**vars(record), 'record_index': index}
        for role, parts, part_index in (('a', a, record.a_index), ('b', b, record.b_index)):
            part = parts[part_index] if part_index is not None else None
            row['name_' + role] = str(part.name) if part else ''
            row['path_' + role] = str(part.path) if part else ''
        uncertain = record.status == 'UNCERTAIN'
        row['verification'] = 'unverified' if uncertain or index in errors else 'confirmed'
        row['diagnostic_reason'] = (str(errors[index]) if index in errors else
            str(overlap.get('reason') or record.note) if uncertain else '')
        # A failed operation identifies its operands, not all uncertain solids.
        failed = overlap.get('failed_pair') or {}
        row['blocked_operation_operand'] = bool(failed and (
            (record.a_index is not None and record.a_index == failed.get('a_index')) or
            (record.b_index is not None and record.b_index == failed.get('b_index'))))
        result.append(row)
    return result


def overview_html(records, context, tolerance, complete, errors=None):
    """Portable summary and diagnostics, with links using stable original indices."""
    alignment = context.get('alignment') or {}
    uncertain = [r for r in records if r['verification'] == 'unverified']
    label = 'Pełna' if complete else 'Częściowa'
    status = f'<section class="panel analysis-overview"><h2>Analiza: {label}</h2>'
    status += f'<p>Tolerancja: {tolerance:g} mm · Pozycje wymagające sprawdzenia: {len(uncertain)}</p>'
    status += '<p>Potwierdzone statusy opisują wynik porównania. Niepotwierdzone różnice nie określają ilości materiału dodanego ani usuniętego.</p>'
    status += '<details><summary>Parametry i identyfikacja źródeł</summary><ul>'
    for role in ('A','B'):
        status += '<li>' + role + ': ' + escape(str(context.get(role) or context.get('source_' + role) or 'Nie podano')) + ' · SHA-256: ' + escape(str((context.get('fingerprints') or {}).get(role, 'Nie podano'))) + '</li>'
    status += '</ul></details>'
    if alignment.get('translation_B_to_A_mm') is not None:
        vector = alignment['translation_B_to_A_mm']
        value = ' · '.join(f'{axis}: {float(n):+.4f} mm' for axis, n in zip('XYZ', vector))
        status += '<h3>Wyrównanie całego złożenia B → A</h3><p>' + escape(value) + '</p>'
        status += '<p>' + ('Zastosowano wyrównanie. Ruchy części podano względem wyrównanego złożenia.' if alignment.get('applied') else 'Nie zastosowano wyrównania; wyniki odnoszą się do oryginalnego położenia.') + '</p>'
    status += '<p>Ruch pojedynczych części: wektory A → B w kolumnach X/Y/Z. Podgląd siatkowy służy do przeglądu; źródłem geometrii pozostaje STEP.</p></section>'
    if uncertain:
        status += '<details class="panel" open><summary>Diagnostyka części wymagających sprawdzenia</summary><ul>'
        for row in uncertain:
            name = row['name_a'] or row['name_b'] or f'Pozycja {row["record_index"] + 1}'
            status += '<li><strong>' + escape(name) + '</strong>: ' + escape(row['diagnostic_reason'])
            if row['blocked_operation_operand']:
                status += ' <b>Element uczestniczył w operacji zakończonej błędem.</b>'
            status += f' <a class="preview-link" href="PODGLAD_KOLOROW_3D.html#pair=PAIR_{row["record_index"]:06d}">Pokaż w 3D</a></li>'
        status += '</ul></details>'
    return status
