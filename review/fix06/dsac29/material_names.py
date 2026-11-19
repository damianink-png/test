"""Name families used ONLY to admit repeated details to material comparison.

Removing a separated revision is a search hint, never a geometry proof.
Keep original names and global rename reporting unchanged.
"""
import re
import unicodedata
from .names import canonical,technical

_REVISION=re.compile(
    r'(?i)[_\s.\-]+(?:(?:rev(?:ision)?|rew(?:izja)?)[_\s.\-]*'
    r'(?:[a-z]{1,2}\d{0,4}|\d{1,4}[a-z]?)|r[_\s.\-]*\d{1,4}[a-z]?)'
    r'(?:[_\s.\-]+\d{1,4})?$')
_SHORT=re.compile(r'(?i)^(?:[a-z]{1,2}\d{0,4}|\d{1,4}[a-z]?)$')
_CODED_REVISION=re.compile(r'(?i)^([a-z]{3,8})\d{1,2}$')


# Exporter's automatically numbered PRODUCT records are not drawing names.
_OCC_EXPORT_PRODUCT=re.compile(
    r'(?i)^open\s+cas(?:cade)?\s+step\s+translator\s+'
    r'\d+(?:\.\d+)*(?:\s+\d+)?$')


def material_name_key(value):
    text=unicodedata.normalize('NFKC',str(value or '')).strip()
    # STEP occurrence indices are not part of the engineering name.
    text=re.sub(r':\d+(?:#\d+)?$','',text).strip()
    text=re.sub(r'\.(?:step|stp)$','',text,flags=re.I)
    # Native CAD object-kind suffix is separate from the revision suffix.
    # Remove it first so 04244035_AF0_PRT and 04244035_AF1 share a family.
    text=re.sub(r'(?i)_PRT$','',text).strip()
    if _OCC_EXPORT_PRODUCT.fullmatch(text):return ''
    if technical(text):return ''
    marked=_REVISION.search(text)
    if marked:
        stem=text[:marked.start()].rstrip('_ .-')
        return canonical(stem) if len(canonical(stem))>=3 else ''
    # Unmarked short revisions must be isolated by an underscore. Do not
    # strip a trailing drawing number from e.g. PART_100 / PART_200.
    if '_' in text:
        stem,suffix=text.rsplit('_',1)
        key=canonical(stem)
        numeric=any(c.isdigit() for c in suffix)
        generic={'part','detal','element','component','komponent','model','solid','shape'}
        short_named_revision=(len(key)>=5 and key not in generic and
                              len(''.join(c for c in suffix if c.isdigit()))<=2)
        meaningful=(len(key)>=3 and
                    (not numeric or any(c.isdigit() for c in key) or short_named_revision))
        coded=_CODED_REVISION.fullmatch(suffix.strip())
        if meaningful and coded:
            # The engineering base is BEFORE the separated revision suffix:
            # czesc1_afm0 / czesc1_xyz2 -> czesc1. Keep preceding middle
            # name fields, so 12345_LEFT_afm0 differs from 12345_RIGHT_afm2.
            # Long numeric drawing codes (AFM100/AFM200) remain untouched.
            return key
        if meaningful and _SHORT.fullmatch(suffix.strip()):return key
    return canonical(text)


def material_name_keys(a,b,proven_pairs=()):
    """Learn a C+numeric exporter convention from independent SAME pairs.

    Never strip a C prefix globally. Three distinct, already verified drawing
    families must demonstrate the convention. A numeric/C-numeric collision
    within the same revision blocks aliasing for that drawing. These keys
    only admit Common candidates; they never prove geometry or rename data.
    """
    keys_a=[material_name_key(p.name) for p in a]
    keys_b=[material_name_key(p.name) for p in b]
    evidence_a=set();evidence_b=set()
    numeric=lambda key:bool(re.fullmatch(r'[0-9]{6,12}',key))
    for i,j in proven_pairs:
        x,y=keys_a[i],keys_b[j]
        if numeric(x) and y=='c'+x:evidence_b.add(x)
        if numeric(y) and x=='c'+y:evidence_a.add(y)
    for keys,evidence in ((keys_a,evidence_a),(keys_b,evidence_b)):
        if len(evidence)<3:continue
        present=set(keys)
        for i,key in enumerate(keys):
            if key.startswith('c') and numeric(key[1:]) and key[1:] not in present:
                keys[i]=key[1:]
    return keys_a,keys_b
