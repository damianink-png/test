from pathlib import Path
import sys
root=Path(sys.argv[1])/'dsac29'
p=root/'step_reexport_tolerance.py';s=p.read_text()
a='def _faces(part):'
assert s.count(a)==1
s=s.replace(a,'''def _faces(part):
    from .boundary_work import cached_faces
    return cached_faces(part, _faces_uncached)


def _faces_uncached(part):''')
a="    report('conservative_bounds_prefilter')"
assert s.count(a)==1
s=s.replace(a,'''    # This path already rejects different face-type multisets below.
    # Decide that before optimal bounds and adaptive integrals on every face;
    # the caller still runs normalization/full solid proof when appropriate.
    from collections import Counter
    def surface_types(shape):
        ex=TopExp_Explorer(shape,TopAbs_FACE);counts=Counter()
        while ex.More():
            counts[str(BRepAdaptor_Surface(TopoDS.Face_s(ex.Current())).GetType())]+=1
            ex.Next()
        return counts
    if surface_types(a.shape)!=surface_types(b.shape):
        report('surface_type_mismatch_requires_normalization')
        return False
'''+a)
p.write_text(s)
p=root/'native_guard.py' ;s=p.read_text()
a='        return _worker_unchecked(request_path, result_path, *args, **kwargs)'
assert s.count(a)==1
s=s.replace(a,'''        from .boundary_work import descriptor_scope
        with descriptor_scope():
            return _worker_unchecked(request_path, result_path, *args, **kwargs)''')
p.write_text(s)
