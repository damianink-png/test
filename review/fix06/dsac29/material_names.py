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
    r'\d+(?:\.\d+)*(?:\s+\d+)?
    text=unicodedata.normalize('NFKC',str(value or '')).strip()
    # STEP occurrence indices are not part of the engineering name.
    text=re.sub(r':\d+(?:#\d+)?$','',text).strip()
    text=re.sub(r'\.(?:step|stp)$','',text,flags=re.I)
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
)


def material_name_key(value):
    text=unicodedata.normalize('NFKC',str(value or '')).strip()
    # STEP occurrence indices are not part of the engineering name.
    text=re.sub(r':\d+(?:#\d+)?$','',text).strip()
    text=re.sub(r'\.(?:step|stp)$','',text,flags=re.I)
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
