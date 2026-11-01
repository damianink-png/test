"""Shared semantic colors for STEP, reports, preview and desktop settings."""
HEX = {
    'SAME':'#94A3B8', 'RENAMED':'#94A3B8',
    'ADDED':'#009E73', 'REMOVED':'#D55E00',
    'MOVED':'#0072B2', 'MOVED_OLD':'#8CC5E3',
    'CHANGED':'#E69F00', 'CHANGED_NEW':'#E69F00', 'CHANGED_OLD':'#F3C977',
    'CHANGED_COMMON':'#94A3B8', 'CHANGED_ADDED':'#009E73', 'CHANGED_REMOVED':'#D55E00',
    'UNCERTAIN':'#CC79A7', 'UNCERTAIN_NEW':'#CC79A7', 'UNCERTAIN_OLD':'#E7B8D0',
}

def rgb(value):
    return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))

COLORS = {k:rgb(HEX[k]) for k in ('SAME','RENAMED','MOVED','CHANGED','ADDED','REMOVED','UNCERTAIN')}
REVISION_COLORS = {k:rgb(v) for k,v in HEX.items()}
MATERIAL_COLORS = {k:rgb(v) for k,v in HEX.items() if k.startswith('CHANGED_') and k not in ('CHANGED_OLD','CHANGED_NEW')}
EXPORT_COLOR_CHOICES = tuple((key,label,HEX[key]) for key,label in (
    ('SAME','Bez zmian / zmiana nazwy'),('ADDED','Nowe elementy B'),
    ('REMOVED','Usunięte elementy A'),('MOVED','Przesunięte — nowe B'),
    ('MOVED_OLD','Przesunięte — stare A'),('CHANGED_NEW','Zmieniona geometria — B'),
    ('CHANGED_OLD','Zmieniona geometria — A'),('CHANGED_COMMON','Materiał wspólny'),
    ('CHANGED_ADDED','Materiał dodany'),('CHANGED_REMOVED','Materiał usunięty'),
    ('UNCERTAIN_NEW','Wymaga weryfikacji — B'),('UNCERTAIN_OLD','Wymaga weryfikacji — A'),
))


def semantic_overrides(colors):
    """Propagate user colors to corresponding STEP/material/preview statuses."""
    result = dict(colors or {})
    for key, aliases in {
        'SAME': ('RENAMED', 'CHANGED_COMMON'),
        'CHANGED': ('CHANGED_NEW',), 'UNCERTAIN': ('UNCERTAIN_NEW',),
        'ADDED': ('CHANGED_ADDED',), 'REMOVED': ('CHANGED_REMOVED',),
    }.items():
        if key in result:
            for alias in aliases:
                result.setdefault(alias, result[key])
    for base, old in (('MOVED','MOVED_OLD'),('CHANGED','CHANGED_OLD'),('UNCERTAIN','UNCERTAIN_OLD')):
        if base in result:
            result.setdefault(old, tuple(float(c)*.55+.45 for c in result[base]))
    return result
