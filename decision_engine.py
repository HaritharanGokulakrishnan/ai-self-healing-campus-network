from collections import Counter

ACTIONS = {
    "normal": "NO_ACTION",
    "link_failure": "REROUTE_VIA_BACKUP_PATH",
    "congestion": "REBALANCE_TRAFFIC_ON_ALTERNATE_PATH",
}


def locate_faulty_host(flagged_pairs):
    """
    Identify the host most strongly associated with flagged link-failure pairs.

    Return None when there is insufficient evidence or the leading
    candidate is tied with another host.
    """
    counts = Counter()

    for pair in flagged_pairs:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            continue

        source, destination = pair

        if not source or not destination or source == destination:
            continue

        counts[source] += 1
        counts[destination] += 1

    if not counts:
        return None

    highest_count = max(counts.values())

    # Require at least two flagged-pair votes for a candidate.
    if highest_count < 2:
        return None

    leaders = [
        host for host, count in counts.items()
        if count == highest_count
    ]

    # Do not guess when multiple hosts have equal evidence.
    if len(leaders) != 1:
        return None

    return leaders[0]


def decide(fault_label, flagged_pairs=()):
    """
    Return a fault label, proposed action, localization status,
    and target host when localization is sufficiently supported.
    """
    if fault_label not in ACTIONS:
        return {
            "fault": fault_label,
            "action": "NO_ACTION",
            "target_host": None,
            "status": "uncertain",
        }

    if fault_label == "normal":
        return {
            "fault": fault_label,
            "action": ACTIONS[fault_label],
            "target_host": None,
            "status": "ok",
        }

    target_host = None

    if fault_label == "link_failure":
        target_host = locate_faulty_host(flagged_pairs)

        if target_host is None:
            return {
                "fault": fault_label,
                "action": "NO_ACTION",
                "target_host": None,
                "status": "uncertain",
            }

    return {
        "fault": fault_label,
        "action": ACTIONS[fault_label],
        "target_host": target_host,
        "status": "ok",
    }


def run_tests():
    tests = [
        (
            "Normal condition",
            decide("normal"),
            "NO_ACTION",
            None,
            "ok",
        ),
        (
            "CS link failure",
            decide(
                "link_failure",
                [
                    ("h_cs", "h_lib"),
                    ("h_cs", "h_admin"),
                    ("h_cs", "h_hos"),
                ],
            ),
            "REROUTE_VIA_BACKUP_PATH",
            "h_cs",
            "ok",
        ),
        (
            "Insufficient evidence",
            decide("link_failure", [("h_cs", "h_lib")]),
            "NO_ACTION",
            None,
            "uncertain",
        ),
        (
            "Tied candidates",
            decide(
                "link_failure",
                [
                    ("h_cs", "h_lib"),
                    ("h_admin", "h_hos"),
                    ("h_cs", "h_admin"),
                    ("h_lib", "h_hos"),
                ],
            ),
            "NO_ACTION",
            None,
            "uncertain",
        ),
        (
            "Empty evidence",
            decide("link_failure", []),
            "NO_ACTION",
            None,
            "uncertain",
        ),
        (
            "Congestion",
            decide("congestion", [("h_lib", "h_cs")]),
            "REBALANCE_TRAFFIC_ON_ALTERNATE_PATH",
            None,
            "ok",
        ),
        (
            "Unknown fault label",
            decide("unexpected_fault", [("h_cs", "h_lib")]),
            "NO_ACTION",
            None,
            "uncertain",
        ),
    ]

    failed = 0

    for name, result, expected_action, expected_target, expected_status in tests:
        passed = (
            result["action"] == expected_action
            and result["target_host"] == expected_target
            and result["status"] == expected_status
        )

        print(f"{'PASS' if passed else 'FAIL'}: {name}")

        if not passed:
            print("  Actual:", result)
            failed += 1

    if failed:
        raise SystemExit(f"{failed} decision-engine test(s) failed.")

    print("\nALL DECISION ENGINE TESTS PASSED")


if __name__ == "__main__":
    run_tests()
