"""Sustained congestion monitoring with optional targeted mitigation."""

import argparse
import time

from congestion_monitor import read_congestion_status
from healer import mitigate_congestion
from congestion_detector import CAPACITY_BPS


def process_congestion_result(
    result,
    mitigate=False,
    mitigated=None,
    cost=100,
    target_link=None,
):
    """Report congestion and optionally mitigate one selected link."""
    if mitigated is None:
        mitigated = set()

    detected = result.get("congested_links", [])
    detected_keys = set()

    for link in detected:
        a, b = link["a"], link["b"]
        key = tuple(sorted((a, b)))
        detected_keys.add(key)

        print(
            f"CONGESTION: {a}-{b} "
            f"{link['utilization_percent']:.2f}% "
            f"({link['rate_bps'] / 1_000_000:.2f} Mbps)",
            flush=True,
        )

        if mitigate and target_link and key == target_link:
            mitigate_congestion((a, b), mitigated, cost=cost)

    if mitigate and target_link and target_link not in detected_keys:
        print(
            f"Target {target_link[0]}-{target_link[1]} "
            "is not currently detected as congested; no mitigation applied.",
            flush=True,
        )

    return detected


def run_monitor(
    interval=2.0,
    mitigate=False,
    cost=100,
    capacity_mbps=CAPACITY_BPS / 1_000_000,
    threshold=80.0,
    samples=3,
    target_link=None,
):
    if interval <= 0:
        raise ValueError("interval must be greater than zero")
    if not 2 <= cost <= 1000:
        raise ValueError("cost must be between 2 and 1000")
    if capacity_mbps <= 0:
        raise ValueError("capacity_mbps must be greater than zero")
    if not 0 < threshold <= 100:
        raise ValueError("threshold must be in (0, 100]")
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if mitigate and target_link is None:
        raise ValueError("--target-link is required when --mitigate is enabled")

    history = {}
    mitigated = set()
    capacity_bps = int(capacity_mbps * 1_000_000)

    print(
        "Congestion monitor started "
        f"(mode={'TARGETED MITIGATION' if mitigate else 'READ-ONLY'}). "
        f"capacity={capacity_mbps:g} Mbps, "
        f"threshold={threshold:g}%, samples={samples}.",
        flush=True,
    )
    if target_link:
        print(
            f"Target link: {target_link[0]}-{target_link[1]}",
            flush=True,
        )
    print("Press Ctrl+C to stop.", flush=True)

    try:
        while True:
            try:
                result = read_congestion_status(
                    history=history,
                    capacity_bps=capacity_bps,
                    threshold_percent=threshold,
                    required_samples=samples,
                )

                print(
                    f"Telemetry: {result['updated_monotonic']} | "
                    f"ports={result['ports_with_rates']} | "
                    f"congested_links={len(result['congested_links'])}",
                    flush=True,
                )

                process_congestion_result(
                    result,
                    mitigate=mitigate,
                    mitigated=mitigated,
                    cost=cost,
                    target_link=target_link,
                )

            except Exception as exc:
                print(f"Monitoring error: {exc}", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nCongestion monitor stopped.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--mitigate",
        action="store_true",
        help="enable targeted routing-cost mitigation",
    )
    parser.add_argument("--target-link", nargs=2, metavar=("SWITCH_A", "SWITCH_B"))
    parser.add_argument("--cost", type=int, default=100)
    parser.add_argument(
        "--capacity-mbps",
        type=float,
        default=CAPACITY_BPS / 1_000_000,
    )
    parser.add_argument("--threshold", type=float, default=80.0)
    parser.add_argument("--samples", type=int, default=3)

    args = parser.parse_args()

    run_monitor(
        interval=args.interval,
        mitigate=args.mitigate,
        cost=args.cost,
        capacity_mbps=args.capacity_mbps,
        threshold=args.threshold,
        samples=args.samples,
        target_link=(
            tuple(sorted(args.target_link))
            if args.target_link
            else None
        ),
    )
