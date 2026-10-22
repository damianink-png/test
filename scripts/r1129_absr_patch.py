"""R11.29: eliminate anonymous ABSR representations caused by occurrence colors."""
import os,json
from pathlib import Path
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/step_io.py"
s=p.read_text("utf8")
def replace(a,b):
    global s
    n=s.count(a)
    if n!=1:raise RuntimeError(f"R11.29 STEP anchor count={n}: {a[:90]!r}")
    s=s.replace(a,b,1)
insert="""def _single_solid_without_wrapper(shape):
    \"\"\"Remove a COMPOUND wrapping exactly one SOLID, retaining its position.\"\"\"
    import os
    from OCP.TopAbs import TopAbs_COMPOUND
    from OCP.TopExp import TopExp_Explorer
    if shape.ShapeType()!=TopAbs_COMPOUND:
        return shape
    solids=list(_solids(shape))
    if os.getenv('DSCOMPARE_STRICT_SOLIDS','0')=='1' and len(solids)!=1:
        raise ValueError(f'DSCOMPARE_STRICT_SOLIDS: oczekiwano jednej bryły, wykryto {len(solids)}')
    if len(solids)!=1:
        return shape
    outside=TopExp_Explorer(shape,TopAbs_FACE,TopAbs_SOLID)
    if outside.More():
        return shape
    return solids[0]


"""
replace("class ColoredDocument:",insert+"class ColoredDocument:")
replace("""        import math
        if not math.isfinite(float(alpha))""",
"""        import math
        name=str(name or '').strip() or f'Element_{self.count+1:04d}'
        if not math.isfinite(float(alpha))""")
replace("""        loc=shape.Location()
        local=shape.Located(TopLoc_Location())""",
"""        import os
        loc=shape.Location()
        local=_single_solid_without_wrapper(shape.Located(TopLoc_Location()))
        if os.getenv('DSCOMPARE_STRICT_SOLIDS','0')=='1':
            count=sum(1 for _ in _solids(local))
            if count!=1:
                raise ValueError(f'DSCOMPARE_STRICT_SOLIDS: {name}: {count} brył zamiast jednej')""")
replace("""        col=Quantity_ColorRGBA(Quantity_Color(*map(float,rgb),Quantity_TOC_RGB),float(alpha))
        for kind in (XCAFDoc_ColorType.XCAFDoc_ColorGen,XCAFDoc_ColorType.XCAFDoc_ColorSurf):
            self.colors.SetColor(occurrence,col,kind)
        if alpha<0.9999:""",
"""        # IMPORTANT: Color labels on referenced occurrences generate two
        # extra anonymous SHAPE_REPRESENTATION entities per occurrence.
        # The product definition and individual faces are colored already.
        if alpha<0.9999:""")
replace("schema=os.getenv('DSCOMPARE_STEP_SCHEMA','AP242DIS')","schema=os.getenv('DSCOMPARE_STEP_SCHEMA','AP214IS')")
replace("if schema not in ('AP214IS','AP242DIS'):schema='AP242DIS'","if schema not in ('AP214IS','AP242DIS'):schema='AP214IS'")
replace("""        Interface_Static.SetIVal_s('write.step.assembly',1)""",
"""        Interface_Static.SetIVal_s('write.step.assembly',1)
        Interface_Static.SetIVal_s('write.step.nonmanifold',0)""")
replace("""                if products!=self.count+assemblies or usages!=wanted_usages:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                diag.update(produkty_step=products,powiazania_zlozenia=usages,""",
"""                if products!=self.count+assemblies or usages!=wanted_usages:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                # Only legitimate status/subassembly containers may generate
                # anonymous SHAPE_REPRESENTATION in hierarchical export.
                reps=len(re.findall(rb'(?m)^#\\d+\\s*=\\s*SHAPE_REPRESENTATION\\(',data))
                if reps>assemblies:
                    raise RuntimeError(f'Nadmiarowe SHAPE_REPRESENTATION powiązane z wystąpieniami: {reps}; dozwolona liczba kontenerów {assemblies}')
                diag.update(puste_reprezentacje_step=max(0,reps-assemblies),
                            anonimowe_reprezentacje_step=reps,
                            kontrola_wstawien_bez_styli=True)
                diag.update(produkty_step=products,powiazania_zlozenia=usages,""")
s=s.replace("STEP assemblies are represented by zero-volume SHAPE_REPRESENTATION", "STEP hierarchy can use legitimate SHAPE_REPRESENTATION")
s=s.replace("products. Some ZW3D versions materialize those as bogus ABSR* parts.", "products. Color on occurrences is the cause of excess anonymous ABSR.")
s=s.replace("'Bez pustych lisci STEP; wyglad importu ZW3D 2019 wymaga weryfikacji'",
            "'Brak kolorów wstawek i nadmiarowych reprezentacji; import ZW3D wymaga potwierdzenia'")
p.write_text(s,encoding="utf8")
print("R11.29 STEP patch: no occurrence colors, single-solid unwrap, AP214, nonmanifold=0, strict optional and surplus guard")
