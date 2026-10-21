#!/usr/bin/env python3
"""
Phase 4: Labeled dataset generation.
Runs normal traffic, then injects link failures and congestion, probing all
host pairs after each step. Each row = one (src,dst) probe, labeled by whether
that pair is affected by the active fault.

    sudo python3 generate_dataset.py --normal 40 --per-fault 10 --output dataset.csv
"""
import argparse, csv, re, time
from datetime import datetime
from mininet.log import setLogLevel, info
from topology import build_campus_topology
from fault_injector import (kill_link, restore_link, start_congestion,
                            stop_congestion, BUILDING_HOST)

LOSS_RE = re.compile(r'(\d+)% packet loss')
RTT_RE = re.compile(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)')
MISSING = 1000.0   # latency value used when no reply was received at all
FIELDS = ['timestamp', 'src', 'dst', 'packet_loss_pct', 'avg_latency_ms',
          'max_latency_ms', 'jitter_ms', 'label']


def probe(src, dst, count=5):
    out = src.cmd('ping -c %d -i 0.2 -W 1 %s' % (count, dst.IP()))
    m = LOSS_RE.search(out)
    loss = float(m.group(1)) if m else 100.0
    r = RTT_RE.search(out)
    if r:
        _, avg, mx, mdev = map(float, r.groups())
    else:
        avg = mx = mdev = MISSING
    return loss, avg, mx, mdev


def sweep(net, writer, f, affected_hosts, fault_label):
    ts = datetime.now().isoformat(timespec='seconds')
    hosts = net.hosts
    for i, h1 in enumerate(hosts):
        for h2 in hosts[i + 1:]:
            loss, avg, mx, jit = probe(h1, h2)
            hit = h1.name in affected_hosts or h2.name in affected_hosts
            writer.writerow({'timestamp': ts, 'src': h1.name, 'dst': h2.name,
                             'packet_loss_pct': loss, 'avg_latency_ms': avg,
                             'max_latency_ms': mx, 'jitter_ms': jit,
                             'label': fault_label if hit else 'normal'})
    f.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--normal', type=int, default=40, help='normal sweeps')
    p.add_argument('--per-fault', type=int, default=10, help='sweeps per fault scenario')
    p.add_argument('--output', default='dataset.csv')
    a = p.parse_args()

    setLogLevel('info')
    net = build_campus_topology(use_remote_controller=False)
    net.start()
    time.sleep(2)

    with open(a.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()

        info('*** Phase A: normal traffic\n')
        for _ in range(a.normal):
            sweep(net, w, f, set(), 'normal')

        info('*** Phase B: link failures\n')
        for b, host in BUILDING_HOST.items():
            kill_link(net, b)
            time.sleep(1)
            for _ in range(a.per_fault):
                sweep(net, w, f, {host}, 'link_failure')
            restore_link(net, b)
            time.sleep(2)

        info('*** Phase C: congestion\n')
        for s, d in [('h_lib', 'h_admin'), ('h_cs', 'h_hos'), ('h_lib', 'h_hos')]:
            start_congestion(net, s, d)
            time.sleep(2)
            for _ in range(a.per_fault):
                sweep(net, w, f, {s, d}, 'congestion')
            stop_congestion(net)
            time.sleep(2)

    net.stop()
    info('*** Dataset written to %s\n' % a.output)


if __name__ == '__main__':
    main()
