from caddiff_palette import PALETTE, appearance
import pytest


def test_category_colors_are_distinct():
    statuses = ('SAME', 'ADDED', 'REMOVED', 'MOVED')
    assert len({appearance(s).hex for s in statuses}) == 4


def test_removed_is_60_percent_transparent():
    assert appearance('REMOVED').opacity == pytest.approx(0.4)


def test_unknown_never_defaults_to_same():
    with pytest.raises(KeyError):
        appearance('UNKNOWN')


def test_valid_hex():
    for style in PALETTE.values():
        assert len(style.hex) == 7 and style.hex.startswith('#')
        int(style.hex[1:], 16)
        assert 0 < style.opacity <= 1
