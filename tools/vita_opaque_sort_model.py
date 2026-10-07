"""Reference model of render-sort-v1 (port/renderer/vita/ww3d_vita_opaque_sort.h).

Pure Python, no compiler. Mirrors the C++ classification, entry eligibility
and planner so the ordering rule can be checked against a small depth-buffer
rasterizer (tools/test_vita_opaque_sort.py) and, when a compiler is allowed,
against the real header (tools/test_vita_opaque_sort_native.py).
"""

OFF, PASS_MAJOR, PASS_MAJOR_GROUPED, IDENTITY = 0, 1, 2, 3
MODES = (OFF, PASS_MAJOR, PASS_MAJOR_GROUPED, IDENTITY)

BASE, BASE_CUTOUT, OVERLAY, BARRIER = 0, 1, 2, 3

# ShaderClass::DepthCompareType
PASS_NEVER, PASS_LESS, PASS_EQUAL, PASS_LEQUAL = 0, 1, 2, 3
PASS_GREATER, PASS_NOTEQUAL, PASS_GEQUAL, PASS_ALWAYS = 4, 5, 6, 7


def classify(blend, depth_write, color_write, alpha_test, depth_compare):
    """Opaque_Sort_Classify."""
    if depth_write:
        if blend or not color_write:
            return BARRIER
        if depth_compare not in (PASS_LESS, PASS_LEQUAL):
            return BARRIER
        return BASE_CUTOUT if alpha_test else BASE
    if depth_compare in (PASS_EQUAL, PASS_LEQUAL):
        return OVERLAY
    return BARRIER


def entry_eligible(batches):
    """Opaque_Sort_Entry_Eligible; batches are dicts with 'pass' and 'cls'."""
    if not batches or batches[0]['pass'] != 0:
        return False
    multipass = False
    for index, batch in enumerate(batches):
        if index and batch['pass'] < batches[index - 1]['pass']:
            return False
        if batch['pass'] != 0:
            multipass = True
    for batch in batches:
        if batch['cls'] == BARRIER:
            return False
        if batch['pass'] != 0:
            continue
        if batch['cls'] == OVERLAY:
            return False
        if multipass and batch['cls'] == BASE_CUTOUT:
            return False
    return True


def state_key(batch):
    """Opaque_Sort_Same_State compares exactly these fields."""
    return (batch['tex0'], batch['tex1'], batch['mat'], batch['shader'], batch['detail'])


def bucket_key(batch):
    """Opaque_Sort_Same_Bucket: the mode-2 grouping key (no vertex material)."""
    return (batch['tex0'], batch['tex1'], batch['shader'], batch['detail'])


def plan(mode, slots):
    """OpaqueSortQueue::Plan over queued batches in submission (slot) order."""
    count = len(slots)
    if mode not in (PASS_MAJOR, PASS_MAJOR_GROUPED):
        return list(range(count))
    order = []
    max_pass = max((batch['pass'] for batch in slots), default=0)
    for current in range(max_pass + 1):
        group = [slot for slot in range(count) if slots[slot]['pass'] == current]
        if mode == PASS_MAJOR_GROUPED:
            first_seen = {}
            for slot in group:
                first_seen.setdefault(bucket_key(slots[slot]), len(first_seen))
            group = sorted(group, key=lambda slot: first_seen[bucket_key(slots[slot])])
        order.extend(group)
    return order


def windows(items):
    """Split a submission sequence the way the renderer queue does.

    items: list of dicts with 'batches' (each batch has 'pass' and 'cls').
    Yields ('queue', [item indices]) and ('now', item index) in order: an
    ineligible item flushes the queue and draws at once.
    """
    queued = []
    for index, item in enumerate(items):
        if entry_eligible(item['batches']):
            queued.append(index)
            continue
        if queued:
            yield ('queue', queued)
            queued = []
        yield ('now', index)
    if queued:
        yield ('queue', queued)


def execution_order(items, mode):
    """(item, batch) pairs in the order the renderer draws them."""
    if mode == OFF:
        return [(i, b) for i, item in enumerate(items) for b in range(len(item['batches']))]
    result = []
    for kind, value in windows(items):
        if kind == 'now':
            result.extend((value, b) for b in range(len(items[value]['batches'])))
            continue
        slots, owners = [], []
        for i in value:
            for b, batch in enumerate(items[i]['batches']):
                slots.append(batch)
                owners.append((i, b))
        result.extend(owners[slot] for slot in plan(mode, slots))
    return result
