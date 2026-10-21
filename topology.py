#!/usr/bin/env python3
"""
Campus network topology (Mininet).

                [Library s2]
                    |
 [CS s3] ---- [Core s1] ---- [Admin s4]
                    |
              [Hostel s5]

redundant=True adds backup links between neighbouring building switches
(s2-s3, s3-s4, s4-s5, s5-s2). They are 'standby' roads used only when a
core link fails.

    sudo python3 topology.py              # plain star, interactive CLI
    sudo python3 topology.py --redundant  # star + backup ring
"""
import json
import sys

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

BACKUP_LINKS = [('s2', 's3'), ('s3', 's4'), ('s4', 's5'), ('s5', 's2')]


def build_campus_topology(use_remote_controller=False, controller_ip='127.0.0.1',
                          controller_port=6653, redundant=False):
    """Build the campus network. Remote controller => switches use 'secure' mode."""
    if use_remote_controller:
        net = Mininet(switch=OVSSwitch, link=TCLink, autoSetMacs=True, controller=None)
        net.addController(RemoteController('c0', ip=controller_ip, port=controller_port))
        mode = 'secure'      # no controller rules => drop (no accidental loops)
    else:
        net = Mininet(switch=OVSSwitch, link=TCLink, autoSetMacs=True, controller=None)
        mode = 'standalone'  # plain learning switch

    core = net.addSwitch('s1', failMode=mode)
    s_lib = net.addSwitch('s2', failMode=mode)
    s_cs = net.addSwitch('s3', failMode=mode)
    s_admin = net.addSwitch('s4', failMode=mode)
    s_hostel = net.addSwitch('s5', failMode=mode)

    h_lib = net.addHost('h_lib', ip='10.0.0.1/24')
    h_cs = net.addHost('h_cs', ip='10.0.0.2/24')
    h_admin = net.addHost('h_admin', ip='10.0.0.3/24')
    h_hos = net.addHost('h_hos', ip='10.0.0.4/24')

    for host, sw in [(h_lib, s_lib), (h_cs, s_cs), (h_admin, s_admin), (h_hos, s_hostel)]:
        net.addLink(host, sw, bw=100)
    for sw in (s_lib, s_cs, s_admin, s_hostel):
        net.addLink(core, sw, bw=1000)

    if redundant:
        for a, b in BACKUP_LINKS:
            net.addLink(net.get(a), net.get(b), bw=1000)
    return net


def export_topology_map(net, path='topo_map.json'):
    """Write switch ids, port numbers, hosts and link types for the controller."""
    topo = {'switches': {}, 'ports': {}, 'hosts': {}, 'links': []}
    for s in net.switches:
        topo['switches'][s.name] = int(s.dpid, 16)
        topo['ports'][s.name] = {}
    for link in net.links:
        n1, n2 = link.intf1.node, link.intf2.node
        p1, p2 = n1.ports[link.intf1], n2.ports[link.intf2]
        if n1 in net.hosts or n2 in net.hosts:
            host, sw, hp, sp = (n1, n2, p1, p2) if n1 in net.hosts else (n2, n1, p2, p1)
            topo['hosts'][host.name] = {'switch': sw.name, 'port': sp,
                                        'mac': host.MAC(), 'ip': host.IP()}
        else:
            topo['ports'][n1.name][n2.name] = p1
            topo['ports'][n2.name][n1.name] = p2
            kind = 'core' if 's1' in (n1.name, n2.name) else 'backup'
            topo['links'].append({'a': n1.name, 'b': n2.name, 'kind': kind})
    with open(path, 'w') as f:
        json.dump(topo, f, indent=2)
    return topo


def main():
    setLogLevel('info')
    net = build_campus_topology(redundant='--redundant' in sys.argv)
    net.start()
    info('\n*** Campus network is up. Testing connectivity...\n')
    net.pingAll()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    main()
