"""
SDN controller app (os-ken, the maintained fork of Ryu).

Installs one rule per host MAC on every switch: "traffic for this host leaves
by this port", using the cheapest working path (core link cost 1, backup link
cost 10). When told a link has failed it recomputes the paths without that link
and rewrites the rules. Commands arrive as JSON on 127.0.0.1:9999:
    {"cmd": "FAIL_LINK", "a": "s1", "b": "s3"}   {"cmd": "RESTORE_LINK", ...}
    {"cmd": "RESET"}   {"cmd": "RELOAD"}   {"cmd": "STATUS"}
"""
import heapq
import json
import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.ofproto import ofproto_v1_3

TOPO_FILE = os.environ.get('TOPO_FILE', 'topo_map.json')
CMD_PORT = int(os.environ.get('HEALER_PORT', '9999'))
COST = {'core': 1, 'backup': 10}
PRIORITY = 10


class HealerApp(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.topo = None
        self.topo_mtime = None
        self.dps = {}          # dpid -> datapath (connected switches)
        self.failed = set()    # failed links, each a frozenset({a, b})
        self.cost_overrides = {}  # link -> temporary routing cost
        self.port_stats_previous = {}
        self.port_stats_current = {}
        self.port_stats_sample_times = {}
        self.port_stats_updated = None
        self.port_stats_interval = 2.0
        hub.spawn(hub.StreamServer(('127.0.0.1', CMD_PORT), self._handle).serve_forever)
        hub.spawn(self._poll_port_stats)

    # ---- topology and routing ----
    def _load_topo(self):
        """(Re)load topo_map.json whenever the file has changed."""
        if not os.path.exists(TOPO_FILE):
            return self.topo is not None
        mtime = os.path.getmtime(TOPO_FILE)
        if mtime != self.topo_mtime:
            with open(TOPO_FILE) as f:
                self.topo = json.load(f)
            self.topo_mtime = mtime
        return True

    def _next_hops(self, dst_sw):
        """Dijkstra from the destination switch: parent[sw] = next hop toward it."""
        adj = {}
        for l in self.topo['links']:
            link = frozenset((l['a'], l['b']))
            cost = getattr(self, 'cost_overrides', {}).get(link, COST[l['kind']])
            adj.setdefault(l['a'], []).append((l['b'], cost))
            adj.setdefault(l['b'], []).append((l['a'], cost))
        dist, parent, queue = {dst_sw: 0}, {}, [(0, dst_sw)]
        while queue:
            d, u = heapq.heappop(queue)
            if d > dist[u]:
                continue
            for v, c in adj.get(u, []):
                if frozenset((u, v)) in self.failed:
                    continue
                if d + c < dist.get(v, 1e9):
                    dist[v], parent[v] = d + c, u
                    heapq.heappush(queue, (d + c, v))
        return parent

    def install_all(self):
        if not self._load_topo():
            return
        by_id = {dpid: name for name, dpid in self.topo['switches'].items()}
        for host in self.topo['hosts'].values():
            parent = self._next_hops(host['switch'])
            for dpid, dp in self.dps.items():
                sw = by_id.get(dpid)
                if sw == host['switch']:
                    port = host['port']
                elif sw in parent:
                    port = self.topo['ports'][sw][parent[sw]]
                else:
                    port = None    # unreachable: remove the stale rule
                self._set_flow(dp, host['mac'], port)

    def _set_flow(self, dp, mac, port):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        match = parser.OFPMatch(eth_dst=mac)
        if port is None:
            mod = parser.OFPFlowMod(datapath=dp, command=ofp.OFPFC_DELETE, match=match,
                                    out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY)
        else:
            actions = [parser.OFPActionOutput(port)]
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=dp, priority=PRIORITY, match=match, instructions=inst)
        dp.send_msg(mod)

    # ---- switch connect / disconnect ----
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change(self, ev):
        if ev.state == MAIN_DISPATCHER:
            self.dps[ev.datapath.id] = ev.datapath
            self.install_all()
        else:
            self.dps.pop(ev.datapath.id, None)

    # ---- OpenFlow port telemetry ----
    def _poll_port_stats(self):
        """Request port counters periodically from connected switches."""
        while True:
            for dp in list(self.dps.values()):
                try:
                    request = dp.ofproto_parser.OFPPortStatsRequest(
                        dp, 0, dp.ofproto.OFPP_ANY
                    )
                    dp.send_msg(request)
                except Exception as exc:
                    self.logger.warning(
                        "Port statistics request failed for switch %s: %s",
                        dp.id, exc
                    )
            hub.sleep(self.port_stats_interval)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply(self, ev):
        """Store per-port counters and calculate rates from that port's prior sample."""
        dp = ev.msg.datapath
        now = time.monotonic()
        current_stats = getattr(self, "port_stats_current", {})
        sample_times = getattr(self, "port_stats_sample_times", {})

        for stat in ev.msg.body:
            key = (dp.id, stat.port_no)
            current = {
                "tx_bytes": stat.tx_bytes,
                "rx_bytes": stat.rx_bytes,
            }
            previous = current_stats.get(key)
            previous_time = sample_times.get(key)

            if previous is not None and previous_time is not None:
                elapsed = now - previous_time
                if elapsed > 0:
                    from port_telemetry import calculate_port_rates
                    rates = calculate_port_rates(
                        {key: previous}, {key: current}, elapsed
                    )
                    if key in rates:
                        current["tx_bps"] = rates[key]["tx_bps"]
                        current["rx_bps"] = rates[key]["rx_bps"]

            current_stats[key] = current
            sample_times[key] = now

        self.port_stats_current = current_stats
        self.port_stats_sample_times = sample_times
        self.port_stats_updated = now

    # ---- command channel ----
    def _handle(self, sock, addr):
        try:
            resp = self._execute(json.loads(sock.recv(4096).decode()))
        except Exception as e:
            resp = {'ok': False, 'error': str(e)}
        sock.sendall((json.dumps(resp) + '\n').encode())
        sock.close()

    def _execute(self, req):
        cmd = req.get('cmd')

        if cmd == 'PORT_STATS':
            topo = self.topo or {}
            by_id = {dpid: name for name, dpid in topo.get('switches', {}).items()}
            rows = []
            for (dpid, port_no), counters in sorted(
                getattr(self, 'port_stats_current', {}).items()
            ):
                row = {
                    'switch': by_id.get(dpid, str(dpid)),
                    'port': port_no,
                    'tx_bytes': counters['tx_bytes'],
                    'rx_bytes': counters['rx_bytes'],
                }
                if 'tx_bps' in counters and 'rx_bps' in counters:
                    row['tx_bps'] = round(counters['tx_bps'], 2)
                    row['rx_bps'] = round(counters['rx_bps'], 2)
                rows.append(row)
            return {
                'ok': True,
                'updated_monotonic': getattr(self, 'port_stats_updated', None),
                'ports': rows,
            }

        if cmd in ('FAIL_LINK', 'RESTORE_LINK',
                   'SET_LINK_COST', 'CLEAR_LINK_COST'):
            a, b = req.get('a'), req.get('b')
            if not isinstance(a, str) or not isinstance(b, str) or a == b:
                return {'ok': False, 'error': 'a and b must be distinct switch names'}

            links = {
                frozenset((link['a'], link['b']))
                for link in (self.topo or {}).get('links', [])
            }
            link = frozenset((a, b))
            if link not in links:
                return {'ok': False, 'error': 'link does not exist in topology'}

            if cmd == 'FAIL_LINK':
                self.failed.add(link)
            elif cmd == 'RESTORE_LINK':
                self.failed.discard(link)
            elif cmd == 'SET_LINK_COST':
                cost = req.get('cost')
                if isinstance(cost, bool) or not isinstance(cost, int) or not 2 <= cost <= 1000:
                    return {'ok': False, 'error': 'cost must be an integer from 2 to 1000'}
                self.cost_overrides[link] = cost
            elif cmd == 'CLEAR_LINK_COST':
                self.cost_overrides.pop(link, None)

        elif cmd == 'RESET':
            self.failed.clear()
            self.cost_overrides.clear()
        elif cmd not in ('STATUS', 'RELOAD'):
            return {'ok': False, 'error': 'unknown command'}

        if cmd != 'STATUS':
            self.install_all()

        return {
            'ok': True,
            'time': time.time(),
            'switches': len(self.dps),
            'failed': sorted(sorted(x) for x in self.failed),
            'cost_overrides': [
                {'a': sorted(link)[0], 'b': sorted(link)[1], 'cost': cost}
                for link, cost in self.cost_overrides.items()
            ],
        }
