"""Read-only STEP scans without copying a potentially gigabyte-sized file.

Mappings and handles are closed before callers rename/delete output on Windows.
Patterns and token counting retain the original structural verification rules.
"""
from contextlib import contextmanager
import mmap
import re


@contextmanager
def mapped_step(path):
    with open(path,'rb') as source:
        if source.seek(0,2)==0:
            yield b''
        else:
            with mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as data:
                yield data


def structure_counts(path):
    with mapped_step(path) as data:
        result={key:sum(1 for _ in re.finditer(re.escape(token),data)) for key,token in (
            ('colors',b'COLOUR_RGB('),('styles',b'STYLED_ITEM('),
            ('alpha',b'SURFACE_STYLE_TRANSPARENT('))}
        for key,token in (('products',b'PRODUCT'),('usages',b'NEXT_ASSEMBLY_USAGE_OCCURRENCE'),('representations',b'SHAPE_REPRESENTATION')):
            pattern=rb'(?m)^#\d+\s*=\s*'+token+rb'\('
            result[key]=sum(1 for _ in re.finditer(pattern,data))
        return result
