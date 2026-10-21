from mininet.log import setLogLevel
from mininet.cli import CLI
from topology import build_campus_topology, export_topology_map

def main():
    setLogLevel('info')
    net = build_campus_topology(
        use_remote_controller=True,
        controller_ip='127.0.0.1',
        controller_port=6653,
        redundant=True
    )
    try:
        net.start()
        net.staticArp()
        export_topology_map(net)
        print("\nCampus topology started. Keep this terminal open.")
        CLI(net)
    finally:
        net.stop()

if __name__ == '__main__':
    main()
