"""STEP exchange identifiers are not engineering part names."""
import re
_TECH=re.compile(r'^(?:(?:=>\s*)?(?:\[[0-9:.,;\s-]+\]|[0-9]+(?::[0-9]+)+)|NAUO[_ -]?\d+|Element_\d+)$',re.I)
def technical(value):
    text=str(value or '').strip()
    return not text or bool(_TECH.fullmatch(text)) or text.casefold() in ('komponent','component','shape','solid')
def canonical(value):
    text=str(value or '').strip()
    if technical(text):return ''
    text=re.sub(r'\.(?:step|stp)$','',text,flags=re.I)
    text=re.sub(r':\d+(?=#\d+$|$)','',text)
    return ''.join(c.casefold() for c in text if c.isalnum())
def genuine_rename(a,b):
    return (getattr(a,'name_origin','explicit')=='explicit' and
            getattr(b,'name_origin','explicit')=='explicit' and
            bool(canonical(a.name)) and bool(canonical(b.name)) and
            canonical(a.name)!=canonical(b.name))
