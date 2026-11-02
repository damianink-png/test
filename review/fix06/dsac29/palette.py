"""Shared semantic colors for STEP, reports, preview and desktop settings."""
HEX = {
    # Exact defaults of the portable desktop UI: one meaning in every output.
    'SAME':'#249B60', 'RENAMED':'#249B60',
    'ADDED':'#168BFF', 'REMOVED':'#FF4050',
    'MOVED':'#A855F7', 'MOVED_OLD':'#D1AAFA',
    # Full CHANGED bodies are amber until verified material regions exist.
    # Verified Common/Cut regions have independent semantic colors.
    'CHANGED':'#F5B82E', 'CHANGED_NEW':'#F5B82E', 'CHANGED_OLD':'#F9D886',
    'CHANGED_COMMON':'#7D899A', 'CHANGED_ADDED':'#168BFF', 'CHANGED_REMOVED':'#FF4050',
    'UNCERTAIN':'#E879C3', 'UNCERTAIN_NEW':'#E879C3', 'UNCERTAIN_OLD':'#F4C4E3',
}

def rgb(value):
    return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))

COLORS = {k:rgb(HEX[k]) for k in ('SAME','RENAMED','MOVED','CHANGED','ADDED','REMOVED','UNCERTAIN')}
REVISION_COLORS = {k:rgb(v) for k,v in HEX.items()}
MATERIAL_COLORS = {k:rgb(v) for k,v in HEX.items() if k.startswith('CHANGED_') and k not in ('CHANGED_OLD','CHANGED_NEW')}
# Ten independently configurable visual layers, in five related pairs.
# Full CHANGED_OLD/NEW fallback remains amber but is not a separate visual
# layer when certified Common/Cut regions exist.
EXPORT_COLOR_CHOICES = tuple((key,label,HEX[key]) for key,label in (
    ('SAME','Bez zmian'),('CHANGED_COMMON','Bez zmian w detalu'),
    ('CHANGED_ADDED','Dodany materiał'),('CHANGED_REMOVED','Usunięty materiał'),
    ('ADDED','Nowe B'),('REMOVED','Usunięte A'),
    ('MOVED_OLD','Przesunięte — stare A'),('MOVED','Przesunięte — nowe B'),
    ('UNCERTAIN_OLD','Do sprawdzenia — A'),('UNCERTAIN_NEW','Do sprawdzenia — B'),
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
