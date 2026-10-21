#!/usr/bin/env python3
"""Phase 3: Fault injection helpers (link failure + congestion) for the campus topology."""
from mininet.log import info

# building -> (core switch, building switch) and the host that lives there
CORE_LINKS = {'LIB': ('s1', 's2'), 'CS': ('s1', 's3'),
              'ADMIN': ('s1', 's4'), 'HOSTEL': ('s1', 's5')}
BUILDING_HOST = {'LIB': 'h_lib', 'CS': 'h_cs', 'ADMIN': 'h_admin', 'HOSTEL': 'h_hos'}


def kill_link(net, building):
    a, b = CORE_LINKS[building]
    info('*** FAULT: link %s-%s (%s) DOWN\n' % (a, b, building))
    net.configLinkStatus(a, b, 'down')


def restore_link(net, building):
    a, b = CORE_LINKS[building]
    info('*** RESTORE: link %s-%s (%s) UP\n' % (a, b, building))
    net.configLinkStatus(a, b, 'up')


def start_congestion(net, src_name, dst_name, bandwidth='150M'):
    """Flood UDP traffic src -> dst above the 100 Mbit host-link capacity."""
    src, dst = net.get(src_name), net.get(dst_name)
    info('*** FAULT: congestion %s -> %s at %s\n' % (src_name, dst_name, bandwidth))
    dst.cmd('iperf -u -s > /dev/null 2>&1 &')
    src.cmd('iperf -u -c %s -b %s -t 3600 > /dev/null 2>&1 &' % (dst.IP(), bandwidth))


def stop_congestion(net):
    info('*** RESTORE: congestion stopped\n')
    for h in net.hosts:
        h.cmd('pkill iperf')
