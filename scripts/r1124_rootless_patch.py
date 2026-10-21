"""R11.24 experimental native grouping without a synthetic top-level assembly.

This variant keeps named status subassemblies and their A/B children. It
removes only the redundant DS Compare wrapper assembly, yielding one fewer
zero-volume STEP PRODUCT. It is opt-in and saved alongside the normal output
for a real ZW3D 2019 importer comparison.
"""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/step_io.py"
s=p.read_text(encoding="utf8")
def sub(old,new):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f'rootless patch anchor mismatch {old[:95]!r}: {n}')
 s=s.replace(old,new,1)

sub("def __init__(self, group_by_status=False, reuse_definitions=True, flat_zw3d=False):",
    "def __init__(self, group_by_status=False, reuse_definitions=True, flat_zw3d=False, rootless_group=False):")
sub("""        self.flat_zw3d=bool(flat_zw3d)
        self.root=None if self.flat_zw3d else self._assembly('DS COMPARE - POROWNANIE REWIZJI')""",
"""        self.flat_zw3d=bool(flat_zw3d)
        self.rootless_group=bool(rootless_group and not self.flat_zw3d and group_by_status)
        # Distinct test: each status group becomes a genuine free XCAF
        # assembly root, not a child of a dummy DS Compare wrapper.
        self.root=None if self.flat_zw3d or self.rootless_group else self._assembly('DS COMPARE - POROWNANIE REWIZJI')""")
sub("""            assembled=XCAFDoc_ShapeTool.GetShape_s(self.root)
            n_solids=sum(1 for _ in _solids(assembled))
            if assembled.IsNull() or n_solids!=self.count:
                raise RuntimeError(f'Niekompletne zlozenie: bryl {n_solids}, oczekiwano {self.count}')
            for label in (self.root,*self._groups.values()):
                components=TDF_LabelSequence()
                if not XCAFDoc_ShapeTool.GetComponents_s(label,components) or components.Length()==0:
                    raise RuntimeError('W strukturze STEP pozostalo puste podzlozenie')""",
"""            if self.rootless_group:
                roots=[v for key,v in self._groups.items() if isinstance(key,str)]
                if not roots:raise RuntimeError('Brak grup w teście STEP bez głównego kontenera')
            else:
                roots=[self.root]
            n_solids=0
            for assembly_root in roots:
                assembled=XCAFDoc_ShapeTool.GetShape_s(assembly_root)
                if assembled.IsNull():raise RuntimeError('Puste złożenie w eksporcie STEP')
                n_solids+=sum(1 for _ in _solids(assembled))
            if n_solids!=self.count:
                raise RuntimeError(f'Niekompletne zlozenie: bryl {n_solids}, oczekiwano {self.count}')
            groups=list(self._groups.values())
            if self.root is not None:groups.insert(0,self.root)
            for label in groups:
                components=TDF_LabelSequence()
                if not XCAFDoc_ShapeTool.GetComponents_s(label,components) or components.Length()==0:
                    raise RuntimeError('W strukturze STEP pozostalo puste podzlozenie')""")
sub("""                assemblies=1+len(self._groups)
                if products!=self.count+assemblies or usages!=self.count+assemblies-1:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                diag.update(produkty_step=products,powiazania_zlozenia=usages,
                            rzeczywiste_bryly_step=self.count,podzlozenia_step=assemblies,
                            samodzielne_puste_produkty=0,grupowanie_zlozenia=True,""",
"""                assemblies=len(self._groups)+(0 if self.rootless_group else 1)
                free_roots=sum(isinstance(k,str) for k in self._groups) if self.rootless_group else 1
                wanted_usages=self.count+assemblies-free_roots
                if products!=self.count+assemblies or usages!=wanted_usages:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                diag.update(produkty_step=products,powiazania_zlozenia=usages,
                            rzeczywiste_bryly_step=self.count,podzlozenia_step=assemblies,
                            samodzielne_puste_produkty=0,grupowanie_zlozenia=True,
                            test_bez_korzenia=bool(self.rootless_group),""")
sub("def _export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None, reuse_definitions=True, flat_zw3d=False):",
    "def _export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None, reuse_definitions=True, flat_zw3d=False, rootless_group=False):")
sub("document=ColoredDocument(group_by_status=True,reuse_definitions=reuse_definitions,flat_zw3d=flat_zw3d)",
    "document=ColoredDocument(group_by_status=True,reuse_definitions=reuse_definitions,flat_zw3d=flat_zw3d,rootless_group=rootless_group)")
needle="""            result['test_absr_step']=str(candidate.relative_to(Path(path).parent))
            result['test_absr_raport']=str(Path(report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: drugi plik STEP jest gotowy w folderze TEST_ABSR.')"""
replacement="""            result['test_absr_step']=str(candidate.relative_to(Path(path).parent))
            result['test_absr_raport']=str(Path(report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: płaski STEP zapisany; teraz test podzłożeń bez zbędnego głównego kontenera...')
            test_group=folder/'GRUPY_BEZ_KORZENIA'
            test_group.mkdir(exist_ok=True)
            group_path=test_group/'STEP_GRUPY_BEZ_KORZENIA.step'
            groups=_export_revision_step(str(group_path),rows,a_parts,b_parts,colors,old_alpha,progress,
                                          reuse_definitions=False,flat_zw3d=False,rootless_group=True)
            groups_report=save_step_diagnostics(group_path,groups)
            result['test_podzlozen_bez_korzenia']=str(group_path.relative_to(Path(path).parent))
            result['test_podzlozen_diagnostyka']=str(Path(groups_report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: dwa pliki testowe gotowe; sprawdź oba w ZW3D 2019.')"""
sub(needle,replacement)
p.write_text(s,encoding='utf8')
print('R11.24 experimental rootless native group export installed')
