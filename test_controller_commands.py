#!/usr/bin/env python3
"""Offline tests for controller link-cost commands."""

from types import SimpleNamespace
from controller_app import HealerApp

topo = {
    'links': [
        {'a': 's1', 'b': 's2', 'kind': 'core'},
        {'a': 's1', 'b': 's3', 'kind': 'core'},
        {'a': 's2', 'b': 's3', 'kind': 'backup'},
    ]
}

def make_app():
    app = SimpleNamespace(
        topo=topo,
        failed=set(),
        cost_overrides={},
        dps={},
        install_all=lambda: None,
    )
    return app

def check(name, condition):
    print(f"{name}: {'PASS' if condition else 'FAIL'}")
    assert condition, name

app = make_app()

# Valid override
r = HealerApp._execute(app, {
    'cmd': 'SET_LINK_COST', 'a': 's1', 'b': 's3', 'cost': 100
})
check('CC1 valid cost override', r['ok'] and app.cost_overrides.get(frozenset(('s1', 's3'))) == 100)

# Invalid link must be rejected
r = HealerApp._execute(app, {
    'cmd': 'SET_LINK_COST', 'a': 's1', 'b': 's9', 'cost': 100
})
check('CC2 invalid link rejected', not r['ok'])

# Invalid cost must be rejected
r = HealerApp._execute(app, {
    'cmd': 'SET_LINK_COST', 'a': 's1', 'b': 's2', 'cost': 1
})
check('CC3 invalid cost rejected', not r['ok'])

# Clear override
r = HealerApp._execute(app, {
    'cmd': 'CLEAR_LINK_COST', 'a': 's1', 'b': 's3'
})
check('CC4 clear override', r['ok'] and not app.cost_overrides)

# RESET clears failed links and overrides
app.failed.add(frozenset(('s1', 's2')))
app.cost_overrides[frozenset(('s2', 's3'))] = 50
r = HealerApp._execute(app, {'cmd': 'RESET'})
check('CC5 reset clears state', r['ok'] and not app.failed and not app.cost_overrides)

print('ALL CONTROLLER COMMAND TESTS PASSED')


# Congestion mitigation lifecycle: penalize link, reroute, restore original route.
app = make_app()

def next_hops(src, dst):
    parent = HealerApp._next_hops(app, dst)
    path = [src]
    while path[-1] != dst:
        hop = parent.get(path[-1])
        if hop is None:
            return None
        path.append(hop)
    return path

original_path = next_hops('s1', 's3')
check('CC6 original route uses direct core link',
      original_path == ['s1', 's3'])

r = HealerApp._execute(app, {
    'cmd': 'SET_LINK_COST', 'a': 's1', 'b': 's3', 'cost': 100
})
mitigated_path = next_hops('s1', 's3')
check('CC7 congestion cost override acknowledged', r['ok'])
check('CC8 alternate route selected',
      mitigated_path == ['s1', 's2', 's3'])

r = HealerApp._execute(app, {
    'cmd': 'CLEAR_LINK_COST', 'a': 's1', 'b': 's3'
})
restored_path = next_hops('s1', 's3')
check('CC9 congestion override cleared', r['ok'])
check('CC10 original route restored',
      restored_path == ['s1', 's3'])

print('ALL CONTROLLER COMMAND AND ROUTING LIFECYCLE TESTS PASSED')
