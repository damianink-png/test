"""Request-local descriptor reuse and lazy, fully verified face matching."""
from contextlib import contextmanager
from contextvars import ContextVar
from collections import deque

_active = ContextVar('boundary_descriptors', default=None)


@contextmanager
def descriptor_scope():
    # Each native request gets its own cache, even in a persistent session.
    token = _active.set({})
    try:
        yield
    finally:
        _active.reset(token)


def cached_faces(part, build):
    cache = _active.get()
    if cache is None:
        return build(part)
    shape = part.shape
    key = (hash(shape), int(shape.Orientation()))
    for saved, result in cache.get(key, ()):
        if shape.IsEqual(saved):
            return result
    result = build(part)
    cache.setdefault(key, []).append((shape, result))
    return result


def verified_face_owner(options, verify, on_unmatched=None, *, scan_all=False):
    """Find a complete bijection, evaluating geometry only on traversed edges.

    Candidate adjacency is not evidence. Every assigned edge must return True
    from the full surface AND wire verifier. Alternating paths preserve valid
    alternatives when a greedy first choice blocks another face.
    """
    owner, reverse, verdicts = {}, {}, {}
    for first in sorted(range(len(options)), key=lambda i: len(options[i])):
        queue = deque([first]); seen_left = {first}; seen_right = set(); parent = {}
        free = None
        while queue and free is None:
            i = queue.popleft()
            for j in options[i]:
                if j in seen_right:
                    continue
                pair = (i, j)
                if pair not in verdicts:
                    verdicts[pair] = bool(verify(i, j))
                if not verdicts[pair]:
                    continue
                seen_right.add(j); parent[j] = i
                if j not in owner:
                    free = j
                    break
                other = owner[j]
                if other not in seen_left:
                    seen_left.add(other); queue.append(other)
        if free is None:
            if on_unmatched is not None:
                on_unmatched(first, seen_left)
            if scan_all:
                continue
            return None
        while True:
            i = parent[free]; old = reverse.get(i)
            owner[free] = i; reverse[i] = free
            if old is None:
                break
            free = old
    return owner
