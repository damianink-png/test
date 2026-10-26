"""Visual-only palette for DS Compare RC9, inspired by caddiff.
No geometry classification or comparison tolerance is modified.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Appearance:
    hex: str
    opacity: float = 1.0

PALETTE = {
    'SAME': Appearance('#86A99B'),
    'ADDED': Appearance('#5C9ED6'),
    'REMOVED': Appearance('#D36B65', 0.4),
    'MOVED': Appearance('#A88ACB'),
    'MATERIAL_ADDED': Appearance('#D86BB4'),
    'MATERIAL_REMOVED': Appearance('#D86BB4'),
}
BACKGROUND = '#252A30'
EDGE = '#65717B'
CHANGE_BOX = '#D36B65'
DISPLACEMENT_ARROW = '#5C9ED6'

def appearance(status: str) -> Appearance:
    """Fail closed on unknown classification; never silently mark it SAME."""
    return PALETTE[status]
