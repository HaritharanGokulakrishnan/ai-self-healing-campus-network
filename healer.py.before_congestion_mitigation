#!/usr/bin/env python3
"""
Automatic self-healing loop + recovery-time experiment.

Each trial cuts one building's core link, then:
  --heal (default): probe network -> ML detects + classifies -> decision engine
                    picks the faulty host -> controller reroutes. Time is measured.
  --no-heal:        nothing is done; we just see whether the network recovers.

Start the controller first (other terminal), then:
    sudo python3 healer.py --trials 8
    sudo python3 healer.py --trials 4 --no-heal --output baseline_results.csv
"""
import argparse
import csv
import re
import statistics
import subprocess
import time

import joblib
import pandas as pd
from mininet.log import setLogLevel

from controller_client import send
from decision_engine import decide
from fault_injector import BUILDING_HOST, CORE_LINKS, kill_link, restore_link
from topology import build_campus_topology, export_topology_map

LOSS_RE = re.compile(r'(\d+)% packet loss')
RTT_RE = re.compile(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)')
MISSING = 1000.0                                  # same filler used for training data
HOST_BUILDING = {h: b for b, h in BUILDING_HOST.items()}


def parse_ping(out):
    """ping text -> (loss %, avg ms, max ms, jitter ms), same as the training data."""
    m = LOSS_RE.search(out)
    loss = float(m.group(1)) if m else 100.0
    r = RTT_RE.search(out)
    if r:
        _, avg, mx, mdev = map(float, r.groups())
        return loss, avg, mx, mdev
    return loss, MISSING, MISSING, MISSING


def probe_all(net):
    """Ping every host pair at the same time; returns [(src, dst, loss, avg, max, jitter)]."""
    jobs = []
    for i, a in enumerate(net.hosts):
        for b in net.hosts[i + 1:]:
            p = a.popen(['ping', '-c', '5', '-i', '0.2', '-W', '1', b.IP()],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            jobs.append((a.name, b.name, p))
    return [(a, b) + parse_ping(p.communicate()[0].decode()) for a, b, p in jobs]


def classify(models, rows):
    """Isolation Forest says 'anything wrong?'; Random Forest says what kind."""
    X = pd.DataFrame([r[2:] for r in rows], columns=models['features'])
    anomalous = models['iso'].predict(X) == -1
    kinds = models['rf'].predict(X)
    return [(r[0], r[1], kind if bad else 'normal')
            for r, kind, bad in zip(rows, kinds, anomalous)]


def heal_if_needed(results, healed):
    """Act only on a localized fault and record healing after controller acknowledgement."""
    congested = [(a, b) for a, b, label in results if label == 'congestion']
    if congested:
        print('    ALERT: congestion on', congested, '(no automatic action yet)')

    flagged = [(a, b) for a, b, label in results if label == 'link_failure']

    if len(flagged) < 2:
        if flagged:
            print('    UNCERTAIN: insufficient link-failure evidence; no action taken')
        return None

    decision = decide('link_failure', flagged)
    target_host = decision.get('target_host')

    if decision.get('status') != 'ok' or target_host not in HOST_BUILDING:
        print('    UNCERTAIN: cannot uniquely localize the faulty link; no action taken')
        return None

    building = HOST_BUILDING[target_host]
    link = CORE_LINKS[building]

    if link in healed:
        return building

    try:
        response = send({'cmd': 'FAIL_LINK', 'a': link[0], 'b': link[1]})
    except Exception as exc:
        print(f'    ERROR: controller communication failed; link not recorded as healed ({exc})')
        return None

    if not isinstance(response, dict) or response.get('ok') is not True:
        print(f'    ERROR: controller did not acknowledge FAIL_LINK: {response!r}')
        return None

    healed.add(link)
    return building


def ping_ok(src, dst):
    return '1 received' in src.cmd('ping -c 1 -W 0.3 %s' % dst.IP())


def run_trial(net, models, building, heal, timeout):
    cut = net.get(BUILDING_HOST[building])
    ref = net.get('h_admin' if building == 'LIB' else 'h_lib')
    healed, detect, recover = set(), None, None

    t0 = time.time()
    kill_link(net, building)
    if heal:
        while time.time() - t0 < timeout and not healed:
            results = classify(models, probe_all(net))
            if detect is None and any(label == 'link_failure' for _, _, label in results):
                detect = time.time() - t0
            heal_if_needed(results, healed)
        while time.time() - t0 < timeout and not ping_ok(ref, cut):
            time.sleep(0.1)
    else:
        while time.time() - t0 < timeout and not ping_ok(ref, cut):
            time.sleep(0.5)
    if ping_ok(ref, cut):
        recover = time.time() - t0

    restore_link(net, building)                   # clean up for the next trial
    send({'cmd': 'RESET'})
    time.sleep(3)
    return detect, recover



def mitigate_congestion(link, mitigated, cost=100):
    """Raise the routing cost of an explicitly identified congested link."""
    if not isinstance(link, (tuple, list)) or len(link) != 2:
        print("    ERROR: expected a link as (switch_a, switch_b)")
        return False

    a, b = link
    key = tuple(sorted((a, b)))

    if key in mitigated:
        print(f"    INFO: congestion mitigation already active for {key}")
        return True

    try:
        response = send({
            "cmd": "SET_LINK_COST",
            "a": a,
            "b": b,
            "cost": cost,
        })
    except Exception as exc:
        print(f"    ERROR: congestion mitigation request failed: {exc}")
        return False

    if not isinstance(response, dict) or response.get("ok") is not True:
        print(f"    ERROR: controller rejected congestion mitigation: {response!r}")
        return False

    mitigated.add(key)
    print(f"    MITIGATION: raised routing cost for {a}-{b} to {cost}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trials', type=int, default=8)
    p.add_argument('--no-heal', action='store_true', help='baseline: healing switched off')
    p.add_argument('--timeout', type=float, default=None, help='seconds to wait per trial')
    p.add_argument('--model', default='model.pkl')
    p.add_argument('--output', default='recovery_results.csv')
    a = p.parse_args()
    heal = not a.no_heal
    timeout = a.timeout or (30 if heal else 15)

    models = joblib.load(a.model)
    setLogLevel('warning')
    net = build_campus_topology(use_remote_controller=True, redundant=True)

    try:
        net.start()
        net.staticArp()
        export_topology_map(net)
        time.sleep(3)
        send({'cmd': 'RELOAD'})
        time.sleep(2)

        mode = 'heal' if heal else 'no-heal'
        print('Mode: %s, trials: %d, timeout: %.0f s' % (mode, a.trials, timeout))
        buildings = list(BUILDING_HOST)
        rows = []

        for i in range(a.trials):
            building = buildings[i % len(buildings)]
            detect, recover = run_trial(net, models, building, heal, timeout)
            rows.append({
                'trial': i + 1,
                'mode': mode,
                'building': building,
                'detect_s': round(detect, 2) if detect else '',
                'recover_s': round(recover, 2) if recover else '',
                'recovered': recover is not None,
            })
            print('  trial %d  cut %-6s  detected %s  recovered %s' % (
                i + 1, building, rows[-1]['detect_s'] or '-',
                rows[-1]['recover_s'] or 'NO'))

        if rows:
            with open(a.output, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)

            ok = [r for r in rows if r['recovered']]
            print('\nRecovered in %d of %d trials' % (len(ok), len(rows)))
            if ok:
                times = [r['recover_s'] for r in ok]
                print('Recovery time: mean %.2f s, min %.2f s, max %.2f s' % (
                    statistics.mean(times), min(times), max(times)))
            print('Saved:', a.output)
    finally:
        net.stop()
        print('Mininet cleanup completed.')


if __name__ == '__main__':
    main()
