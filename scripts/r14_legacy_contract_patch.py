"""Update the one historical confirmation expectation for R14 auto-alignment."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'source'/'tests'/'test_r7_alignment_preview.py'
s=p.read_text(encoding='utf-8')
old="""    assert len(approvals)==1
    assert np.allclose(approvals[0]['translation_B_to_A_mm'],-shift)"""
new="""    # R14 automatically applies an unambiguous, B-Rep-verified 231/380 shift.
    assert not approvals
    assert np.allclose(summary['alignment']['translation_B_to_A_mm'],-shift)
    assert summary['alignment']['approved_by_user'] is False"""
if s.count(old)!=1:
    raise RuntimeError('Historical test did not match the R13 source baseline')
p.write_text(s.replace(old,new,1),encoding='utf-8')
print('R14 revised legacy confirmation regression PASS')
