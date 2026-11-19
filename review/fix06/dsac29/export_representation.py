"""Cheap definition-local routing hints; never an equality certificate."""
from collections import Counter


class RepresentationCache:
    def __init__(self):
        self.profiles = {}

    def profile(self, part, definition):
        if definition not in self.profiles:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from OCP.TopAbs import TopAbs_FACE
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopoDS import TopoDS
            counts = Counter()
            faces = TopExp_Explorer(part.shape, TopAbs_FACE)
            while faces.More():
                counts[str(BRepAdaptor_Surface(TopoDS.Face_s(faces.Current())).GetType())] += 1
                faces.Next()
            self.profiles[definition] = tuple(sorted(counts.items()))
        return self.profiles[definition]

    def differs(self, left, right, left_definition, right_definition):
        return self.profile(left, left_definition) != self.profile(right, right_definition)
