from pathlib import Path
from tempfile import TemporaryDirectory
from dsac29.exact_brep_identity import identical_serialized_brep

def test_identity():
    with TemporaryDirectory() as d:
        a,b=Path(d)/'a',Path(d)/'b'
        a.write_bytes(b'abc');b.write_bytes(b'abc')
        assert identical_serialized_brep(a,b)
        b.write_bytes(b'abd')
        assert not identical_serialized_brep(a,b)
