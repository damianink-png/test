import {it,expect} from 'vitest';
import {massSummary,stepPaths,hasTranslation,defaults,paletteKeys,paletteLabels,restorePalette} from '../src/model';
it('formats the actual mass worker payload and rejects missing totals',()=>{expect(massSummary({masa_calosci_kg:44.931862,liczba_bryl:553,liczba_plikow:1,gestosc_kg_m3:7850})).toEqual({mass:44.931862,solids:553,models:1,density:7850});expect(massSummary(null)).toBeNull();expect(massSummary({masa_calosci_kg:Infinity})).toBeNull()});
it('accepts Windows, Unicode and uppercase STEP drops but rejects folders and other files',()=>{expect(stepPaths(['C:\\Modele\\Osłona.STEP','C:\\Modele\\Osłona.STEP','D:\\B.stp'])).toHaveLength(2);expect(()=>stepPaths(['C:\\folder'])).toThrow();expect(()=>stepPaths(['A.step','B.exe'])).toThrow()});
it('does not present unresolved placeholders as a measured zero shift',()=>{const q={token:'t',material_unverified:false,reason:'',unverified_A:0,unverified_B:0,translation_mm:[0,0,0]};expect(hasTranslation(q)).toBe(false);expect(hasTranslation({...q,translation_mm:[507.4569,-249.1752,524]})).toBe(true);expect(hasTranslation({...q,unresolved:true,translation_mm:[1,2,3]})).toBe(false);expect(defaults.bomCsv).toBe(false)});

it('shows exactly ten independently editable categories in five related pairs',()=>{
 const keys=['same','changed_common','changed_added','changed_removed','added','removed','moved_old','moved','uncertain_old','uncertain_new'];
 expect([...paletteKeys]).toEqual(keys);expect(Object.keys(defaults.palette)).toEqual(keys);
 expect(Object.keys(paletteLabels)).toEqual(keys);
 expect(paletteLabels.changed_common).toBe('Bez zmian w detalu');
 expect(defaults.palette.changed_common).toBe('#7d899a');
 expect(defaults.palette.changed_added).toBe('#168bff');
 expect(defaults.palette.changed_removed).toBe('#ff4050');
 expect(defaults.oldAlpha).toBe(0.4);
 expect(keys.map(k=>k.toUpperCase())).toContain('CHANGED_COMMON');
});
it('migrates legacy colors without losing custom A/B or Common/Cut overrides',()=>{
 const p=restorePalette({added:'#009e73',changed:'#e69f00',removed:'#123456',same:'#94a3b8',common:'#aabbcc',uncertain:'#a1b2c3'});
 expect(p.added).toBe('#168bff');expect(p.changed_added).toBe('#168bff');
 expect(p.removed).toBe('#123456');expect(p.changed_removed).toBe('#123456');
 expect(p.same).toBe('#249b60');expect(p.changed_common).toBe('#aabbcc');
 expect(p.uncertain_old).toBe('#a1b2c3');expect(p.uncertain_new).toBe('#a1b2c3');
 const custom=restorePalette({added:'#123456',changed_added:'#abcdef',moved:'#112233',moved_old:'#123456',uncertain_old:'#654321',uncertain_new:'#111111'});
 expect(custom.added).toBe('#123456');expect(custom.changed_added).toBe('#abcdef');
 expect(custom.moved_old).toBe('#123456');expect(custom.uncertain_old).toBe('#654321');
 expect(custom.uncertain_new).toBe('#111111');
});
