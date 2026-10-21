#!/usr/bin/env python3
"""Offline test of the controller's path logic (no Mininet, no sudo needed).
    python3 test_routing.py
"""
from types import SimpleNamespace
from controller_app import HealerApp

CORE = [('s1', 's2'), ('s1', 's3'), ('s1', 's4'), ('s1', 's5')]
BACKUP = [('s2', 's3'), ('s3', 's4'), ('s4', 's5'), ('s5', 's2')]
topo = {'links': [{'a': a, 'b': b, 'kind': 'core'} for a, b in CORE] +
                  [{'a': a, 'b': b, 'kind': 'backup'} for a, b in BACKUP]}
HOST_SW = {'h_lib': 's2', 'h_cs': 's3', 'h_admin': 's4', 'h_hos': 's5'}


def path(src, dst, failed, cost_overrides=None):
    """Follow next hops from src's switch to dst's switch."""
    app = SimpleNamespace(
        topo=topo,
        failed={frozenset(f) for f in failed},
        cost_overrides=cost_overrides or {},
    )
    parent = HealerApp._next_hops(app, HOST_SW[dst])
    node, hops = HOST_SW[src], [HOST_SW[src]]
    while node != HOST_SW[dst]:
        if node not in parent:
            return None                      # unreachable
        node = parent[node]
        hops.append(node)
    return hops


tests = [
    ('TC-R1 healthy: cs -> lib uses core', 'h_cs', 'h_lib', [], ['s3', 's1', 's2']),
    ('TC-R2 s1-s3 down: cs -> lib uses backup', 'h_cs', 'h_lib', [('s1', 's3')], ['s3', 's2']),
    ('TC-R3 s1-s3 down: cs -> hos detours', 'h_cs', 'h_hos', [('s1', 's3')], ['s3', 's2', 's1', 's5']),
    ('TC-R4 s1-s3 down: lib -> admin unaffected', 'h_lib', 'h_admin', [('s1', 's3')], ['s2', 's1', 's4']),
    ('TC-R5 s1-s3 + s3-s2 down: cs -> lib via s4', 'h_cs', 'h_lib', [('s1', 's3'), ('s3', 's2')], ['s3', 's4', 's1', 's2']),
]
for name, src, dst, failed, expected in tests:
    got = path(src, dst, failed)
    print('%-46s %-22s %s' % (name, '->'.join(got or ['NONE']), 'PASS' if got == expected else 'FAIL'))
    assert got == expected, (got, expected)

# TC-R6: raising the direct s1-s3 cost should move CS -> LIB to s3-s2.
override = {frozenset(('s1', 's3')): 100}
got = path('h_cs', 'h_lib', [], override)
expected = ['s3', 's2']
print('%-46s %-22s %s' % (
    'TC-R6 congestion cost override',
    '->'.join(got or ['NONE']),
    'PASS' if got == expected else 'FAIL',
))
assert got == expected, (got, expected)

print('ALL ROUTING TESTS PASSED')
