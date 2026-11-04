"""Conservative recovery of reversible Polish-name mojibake from STEP XCAF.

Never reconstruct U+FFFD (the original byte has already been lost), never
alter valid Unicode and preserve engineering units such as mm³.
"""
from __future__ import annotations
import re
import unicodedata

# UTF-8 byte sequences accidentally interpreted as Windows-1252.
_UTF8_MOJIBAKE = re.compile(r"(?:Å[‚¼º¹]|Ä[…‡™„†]|Ã[³±]|Å[›º])")

# CP1250 bytes interpreted as ISO-8859-1 or Windows-1252.
# Only apply this table when a strong sign of a mistaken encoding exists.
_CP1250 = {
    "³": "ł", "£": "Ł", "¹": "ą", "¥": "Ą", "¿": "ż", "¯": "Ż",
    "ê": "ę", "Ê": "Ę", "æ": "ć", "Æ": "Ć", "ñ": "ń", "Ñ": "Ń",
    "œ": "ś", "\u0152": "Ś", "\u009c": "ś", "\u008c": "Ś",
    "\u009f": "ź", "\u008f": "Ź",
}


def repair_polish_name(value: str) -> str:
    name = unicodedata.normalize("NFC", str(value))
    if _UTF8_MOJIBAKE.search(name):
        try:
            decoded = name.encode("cp1252").decode("utf-8")
            if any(ch in decoded for ch in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"):
                name = decoded
        except (UnicodeError, LookupError):
            pass

    # A superscript 3 at the END of an engineering unit (mm³) is legitimate.
    # 'P³yta', 'ko³a' and 'g³ówny' are reversibly damaged CP1250.
    strong = any(x in name for x in ("¹", "¿", "£", "¥", "¯", "\u009c", "\u008c", "\u009f", "\u008f")) or \
             bool(re.search(r"(?<=[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż])³(?=[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż])",name))
    if not strong:
        return name
    fixed = []
    for index,ch in enumerate(name):
        target = _CP1250.get(ch)
        if target is None:
            fixed.append(ch)
            continue
        previous = name[index-1] if index else ""
        following = name[index+1] if index+1<len(name) else ""
        # Avoid changing technical symbols and numerical superscripts.
        if ch == "³" and not (previous.isalpha() and following.isalpha()):
            fixed.append(ch)
        elif previous.isalpha() or following.isalpha():
            fixed.append(target)
        else:
            fixed.append(ch)
    return "".join(fixed)
