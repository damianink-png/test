"""DS Compare R11.19: restore native status subassemblies and verify no empty leaf products."""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29"/"step_io.py"
s=p.read_text(encoding="utf8")
old="""        if not self.flat_zw3d:self.tool.UpdateAssemblies()
        writer=STEPCAFControl_Writer();writer.SetNameMode(True);writer.SetColorMode(True);writer.SetLayerMode(True)"""
new="""        if not self.flat_zw3d:
            self.tool.UpdateAssemblies()
            # Every status subassembly must contain genuine SOLID descendants.
            from OCP.XCAFDoc import XCAFDoc_ShapeTool
            from OCP.TDF import TDF_LabelSequence
            assembled=XCAFDoc_ShapeTool.GetShape_s(self.root)
            n_solids=sum(1 for _ in _solids(assembled))
            if assembled.IsNull() or n_solids!=self.count:
                raise RuntimeError(f'Niekompletne zlozenie: bryl {n_solids}, oczekiwano {self.count}')
            for label in (self.root,*self._groups.values()):
                components=TDF_LabelSequence()
                if not XCAFDoc_ShapeTool.GetComponents_s(label,components) or components.Length()==0:
                    raise RuntimeError('W strukturze STEP pozostalo puste podzlozenie')
        writer=STEPCAFControl_Writer();writer.SetNameMode(True);writer.SetColorMode(True);writer.SetLayerMode(True)"""
assert s.count(old)==1, "assembly update anchor not found"
s=s.replace(old,new,1)
old="""            if self.flat_zw3d:
                # Structural regression: no empty compound assembly shells or"""
new="""            if not self.flat_zw3d:
                import re
                data=temporary.read_bytes()
                # Containers MUST remain to support subassemblies; reject
                # surplus zero-volume PRODUCT leaves rather than flattening.
                products=len(re.findall(rb'(?m)^#\d+\s*=\s*PRODUCT\(',data))
                usages=len(re.findall(rb'(?m)^#\d+\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\(',data))
                assemblies=1+len(self._groups)
                if products!=self.count+assemblies or usages!=self.count+assemblies-1:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                diag.update(produkty_step=products,powiazania_zlozenia=usages,
                            rzeczywiste_bryly_step=self.count,podzlozenia_step=assemblies,
                            samodzielne_puste_produkty=0,grupowanie_zlozenia=True,
                            uwaga_absr='Bez pustych lisci STEP; wyglad importu ZW3D 2019 wymaga weryfikacji')
            if self.flat_zw3d:
                # Structural regression: no empty compound assembly shells or"""
assert s.count(old)==1,"structural verification anchor not found"
s=s.replace(old,new,1)
old="""    # No empty products in STEP. This manifest preserves the former status
    # hierarchy for a future validated ZW3D-native grouping command. It is
    # deliberately NOT presented as a native assembly that already exists.
    manifest=Path(path).with_name('GRUPY_ZW3D.json')
    manifest.write_text(json.dumps({'format':'dscompare-subassembly-groups-v1',
        'status':'wymaga_zweryfikowanego_grupowania_przez_api_zw3d',
        'STEP':Path(path).name,'liczba_bryl':document.count,
        'grupy':product_groups},ensure_ascii=False,indent=2),encoding='utf8')"""
new="""    # STEP already contains actual native parent/child references.
    manifest=Path(path).with_name('GRUPY_ZW3D.json')
    manifest.write_text(json.dumps({'format':'dscompare-subassembly-groups-v2',
        'status':'natywne_podzlozenia_step' if not flat_zw3d else 'plaskie_warstwy_step',
        'STEP':Path(path).name,'liczba_bryl':document.count,
        'uwaga':'Nie ma pustych lisci; ZW3D 2019 moze inaczej przedstawic kontenery',
        'grupy':product_groups},ensure_ascii=False,indent=2),encoding='utf8')"""
assert s.count(old)==1,"manifest anchor not found"
s=s.replace(old,new,1)
start=s.index('def export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None):')
s=s[:start]+'''def export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None):
    """Restore real status subassemblies with independent solid STEP products.

    XCAF parent assembly nodes are necessary and cannot be removed as "empty
    parts"; every *leaf* must be a verified positive-volume SOLID.
    """
    import os
    flat=os.environ.get('DSCOMPARE_FLAT_FALLBACK','0')=='1'
    result=_export_revision_step(path,list(records),a_parts,b_parts,colors,old_alpha,progress,
                                 reuse_definitions=False,flat_zw3d=flat)
    result['tryb_zapisu']='plaski_awaryjny' if flat else 'podzlozenia_bez_pustych_lisci'
    return result
'''
p.write_text(s,encoding='utf8')
p=root/"dsac29"/"worker_v37.py"
s=p.read_text('utf8')
old="os.environ['DSCOMPARE_SAFE_EXPORT']='1'  # legacy STEP containers disabled to prevent ABSR"
assert s.count(old)==1,"worker export anchor not found"
s=s.replace(old,"os.environ['DSCOMPARE_SAFE_EXPORT']='0'  # native status subassemblies, no phantom leaf products",1)
p.write_text(s,encoding='utf8')
p=root/"dsac29"/"gui_modern.py"
s=p.read_text('utf8')
s=s.replace('  # This unsafe option is intentionally retired: export always writes solid-only STEP.','  # Flat/legacy switch retired: validated native hierarchy is the only visible export.')
p.write_text(s,encoding='utf8')
(root/"VERSION.txt").write_text("R11.19\n",encoding="utf8")
print("R11.19 native group exporter installed")
