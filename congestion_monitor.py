"""Read-only adapter for controller telemetry and congestion detection."""

import argparse
import json
import time

from controller_client import send
from congestion_detector import CAPACITY_BPS, detect_congested_links


def read_congestion_status(
    topology_path="topo_map.json",
    history=None,
    capacity_bps=CAPACITY_BPS,
    threshold_percent=80.0,
    required_samples=3,
):
    if history is None:
        history = {}

    with open(topology_path) as f:
        topology = json.load(f)

    response = send({"cmd": "PORT_STATS"})
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(f"PORT_STATS request failed: {response!r}")

    port_stats = {}
    for row in response.get("ports", []):
        if "tx_bps" not in row or "rx_bps" not in row:
            continue
        port_stats[(row["switch"], row["port"])] = {
            "tx_bps": float(row["tx_bps"]),
            "rx_bps": float(row["rx_bps"]),
        }

    congested = detect_congested_links(
        topology,
        port_stats,
        history,
        threshold_percent=threshold_percent,
        required_samples=required_samples,
        capacity_bps=capacity_bps,
    )

    return {
        "updated_monotonic": response.get("updated_monotonic"),
        "ports_with_rates": len(port_stats),
        "congested_links": congested,
        "history": history,
    }


def display_status(result):
    print("Telemetry timestamp:", result["updated_monotonic"])
    print("Ports with rates:", result["ports_with_rates"])

    if result["congested_links"]:
        for link in result["congested_links"]:
            print(
                f"CONGESTION: {link['a']}-{link['b']} "
                f"{link['utilization_percent']:.2f}% "
                f"({link['rate_bps'] / 1_000_000:.2f} Mbps)"
            )
    else:
        print("No link has met the sustained congestion threshold.")

    print("-" * 55, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--capacity-mbps", type=float,
        default=CAPACITY_BPS / 1_000_000,
    )
    parser.add_argument("--threshold", type=float, default=80.0)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.capacity_mbps <= 0:
        parser.error("--capacity-mbps must be greater than zero")
    if not 0 < args.threshold <= 100:
        parser.error("--threshold must be in (0, 100]")
    if args.samples < 1:
        parser.error("--samples must be at least 1")

    capacity_bps = int(args.capacity_mbps * 1_000_000)
    history = {}

    print(
        f"Capacity: {args.capacity_mbps:g} Mbps | "
        f"Threshold: {args.threshold:g}% | "
        f"Required samples: {args.samples}",
        flush=True,
    )

    def poll():
        result = read_congestion_status(
            history=history,
            capacity_bps=capacity_bps,
            threshold_percent=args.threshold,
            required_samples=args.samples,
        )
        display_status(result)

    if not args.watch:
        poll()
        return

    print("Read-only congestion monitor started. Press Ctrl+C to stop.",
          flush=True)
    try:
        while True:
            try:
                poll()
            except Exception as exc:
                print(f"Monitoring error: {exc}", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nCongestion monitor stopped.", flush=True)


if __name__ == "__main__":
    main()
