#!/usr/bin/env python3
"""
First live proof of healing: cut a link, then tell the controller to reroute.
Start the controller first (other terminal), then:
    sudo python3 manual_heal_test.py
Expected: 1 healthy True / 2 after cut False / 3 recovered True (about a second).
"""
import subprocess
import time
from mininet.log import setLogLevel
from topology import build_campus_topology, export_topology_map
from fault_injector import kill_link, restore_link
from controller_client import send


def ping_ok(src, dst):
    return '1 received' in src.cmd('ping -c 1 -W 1 %s' % dst.IP())


setLogLevel('warning')
net = build_campus_topology(use_remote_controller=True, redundant=True)
net.start()
net.staticArp()
export_topology_map(net)            # after start: host MACs are final only now
time.sleep(3)                       # let the switches connect
send({'cmd': 'RELOAD'})             # controller reads the map and installs rules
time.sleep(2)

lib, cs = net.get('h_lib'), net.get('h_cs')
print('switches connected  :', send({'cmd': 'STATUS'})['switches'], '(expect 5)')
print('1 healthy ping      :', ping_ok(lib, cs))
if not ping_ok(lib, cs):            # diagnostics, only printed when something is wrong
    print('--- s3 flow table ---')
    print(subprocess.run('ovs-ofctl -O OpenFlow13 dump-flows s3', shell=True,
                         capture_output=True, text=True).stdout)
    print('host MACs:', {h.name: h.MAC() for h in net.hosts})

kill_link(net, 'CS')
print('2 ping after cut    :', ping_ok(lib, cs), '(expect False)')

t0 = time.time()
send({'cmd': 'FAIL_LINK', 'a': 's1', 'b': 's3'})
while not ping_ok(lib, cs) and time.time() - t0 < 10:
    time.sleep(0.1)
print('3 recovered         :', ping_ok(lib, cs), 'in %.2f s after the reroute command' % (time.time() - t0))

restore_link(net, 'CS')
send({'cmd': 'RESET'})
net.stop()
