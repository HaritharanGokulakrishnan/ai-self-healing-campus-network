"""Pure helpers for calculating OpenFlow port traffic rates."""

def calculate_port_rates(previous, current, elapsed):
    """Calculate TX/RX bit rates from two byte-counter snapshots."""
    if elapsed <= 0:
        raise ValueError("elapsed must be positive")

    results = {}
    for key, now in current.items():
        before = previous.get(key)
        if before is None:
            continue

        tx_delta = now["tx_bytes"] - before["tx_bytes"]
        rx_delta = now["rx_bytes"] - before["rx_bytes"]

        # Counters may reset or wrap; don't report negative rates.
        if tx_delta < 0 or rx_delta < 0:
            continue

        results[key] = {
            "tx_bps": tx_delta * 8 / elapsed,
            "rx_bps": rx_delta * 8 / elapsed,
        }

    return results


def utilization(rate_bps, capacity_bps):
    """Return link utilization as a percentage."""
    if capacity_bps <= 0:
        raise ValueError("capacity_bps must be positive")
    return max(0.0, rate_bps) / capacity_bps * 100.0
