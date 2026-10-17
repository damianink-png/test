"""Additional Excel-facing BOM compatibility checks."""
from dsac29.report import _csv_value

def test_part_number_with_leading_zero_kept_when_excel_opens_csv():
    assert _csv_value('04244036') == '=\"04244036\"'
    assert _csv_value('123456') == '123456'

def test_untrusted_names_do_not_execute_formulas():
    assert _csv_value('=HYPERLINK("https://evil.example")').startswith("'=")
    assert _csv_value('+2+2').startswith("'+")
