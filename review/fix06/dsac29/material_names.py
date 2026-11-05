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


def material_name_key(value):
    text=unicodedata.normalize('NFKC',str(value or '')).strip()
    text=re.sub(r'\.(?:step|stp)$','',text,flags=re.I)
    if technical(text):return ''
    # STEP occurrence indices are not part of the engineering name.
    text=re.sub(r':\d+(?:#\d+)?$','',text).strip()
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
        meaningful=(len(key)>=3 and
                    (not numeric or any(c.isdigit() for c in key)))
        if meaningful and _SHORT.fullmatch(suffix.strip()):return key
    return canonical(text)
