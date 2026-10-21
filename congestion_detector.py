
"""Read-only detection of sustained congestion on switch-to-switch links."""

from port_telemetry import utilization

CAPACITY_BPS = 1_000_000_000
DEFAULT_THRESHOLD_PERCENT = 80.0
DEFAULT_REQUIRED_SAMPLES = 3


def detect_congested_links(
    topology,
    port_stats,
    history,
    threshold_percent=DEFAULT_THRESHOLD_PERCENT,
    required_samples=DEFAULT_REQUIRED_SAMPLES,
    capacity_bps=CAPACITY_BPS,
):
    """Return links above the utilization threshold for consecutive samples.

    Args:
        topology: Network topology containing links and switch port mappings.
        port_stats: Mapping of (switch_name, port_number) to TX/RX rates.
        history: Mutable mapping of sorted switch-pair keys to consecutive
            high-utilization sample counts.
        threshold_percent: Utilization percentage that triggers detection.
        required_samples: Number of consecutive high samples required.
        capacity_bps: Assumed link capacity in bits per second. Defaults
            to 1 Gbps; can be lowered for controlled testing.

    Returns:
        A list of detected congested links. This function does not change
        network routing.
    """
    if not 0 < threshold_percent <= 100:
        raise ValueError("threshold_percent must be in (0, 100]")

    if required_samples < 1:
        raise ValueError("required_samples must be at least 1")

    if capacity_bps <= 0:
        raise ValueError("capacity_bps must be positive")

    detected = []
    ports = topology.get("ports", {})

    for link in topology.get("links", []):
        a, b = link["a"], link["b"]

        if b not in ports.get(a, {}) or a not in ports.get(b, {}):
            continue

        key = tuple(sorted((a, b)))
        port_a = ports[a][b]
        port_b = ports[b][a]

        stat_a = port_stats.get((a, port_a))
        stat_b = port_stats.get((b, port_b))

        # Both switch endpoints must have complete rate measurements.
        if stat_a is None or stat_b is None:
            history[key] = 0
            continue

        required_fields = ("tx_bps", "rx_bps")
        if any(
            field not in stat_a or field not in stat_b
            for field in required_fields
        ):
            history[key] = 0
            continue

        # Use the busiest observed direction without double-counting
        # corresponding TX/RX traffic at the two endpoints.
        rate_bps = max(
            float(stat_a["tx_bps"]),
            float(stat_a["rx_bps"]),
            float(stat_b["tx_bps"]),
            float(stat_b["rx_bps"]),
        )

        percent = utilization(rate_bps, capacity_bps)

        if percent >= threshold_percent:
            history[key] = history.get(key, 0) + 1
        else:
            history[key] = 0

        if history[key] >= required_samples:
            detected.append({
                "a": a,
                "b": b,
                "kind": link.get("kind"),
                "utilization_percent": round(percent, 2),
                "rate_bps": rate_bps,
            })

    return detected
