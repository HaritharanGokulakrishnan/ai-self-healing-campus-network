import unittest

from congestion_detector import detect_congested_links


class CongestionDetectorTests(unittest.TestCase):
    def setUp(self):
        self.topology = {
            "ports": {
                "s1": {"s2": 1},
                "s2": {"s1": 2},
            },
            "links": [{"a": "s1", "b": "s2", "kind": "core"}],
        }
        self.history = {}

    def stats(self, tx_a, tx_b):
        return {
            ("s1", 1): {"tx_bps": tx_a, "rx_bps": 0},
            ("s2", 2): {"tx_bps": tx_b, "rx_bps": 0},
        }

    def test_requires_three_consecutive_high_samples(self):
        stats = self.stats(850_000_000, 100_000_000)

        for _ in range(2):
            self.assertEqual(
                detect_congested_links(self.topology, stats, self.history),
                [],
            )

        result = detect_congested_links(
            self.topology, stats, self.history
        )

        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["a"], result[0]["b"]), ("s1", "s2"))
        self.assertEqual(result[0]["utilization_percent"], 85.0)

    def test_below_threshold_resets_history(self):
        self.history[("s1", "s2")] = 2

        result = detect_congested_links(
            self.topology,
            self.stats(500_000_000, 100_000_000),
            self.history,
        )

        self.assertEqual(result, [])
        self.assertEqual(self.history[("s1", "s2")], 0)

    def test_missing_rate_resets_history(self):
        self.history[("s1", "s2")] = 2

        result = detect_congested_links(
            self.topology,
            {("s1", 1): {"tx_bps": 900_000_000}},
            self.history,
        )

        self.assertEqual(result, [])
        self.assertEqual(self.history[("s1", "s2")], 0)

    def test_invalid_threshold_rejected(self):
        with self.assertRaises(ValueError):
            detect_congested_links(
                self.topology,
                self.stats(0, 0),
                self.history,
                threshold_percent=0,
            )

    def test_custom_capacity_detects_congestion(self):
        # 42 Mbps is 84% of the configured 50 Mbps capacity.
        stats = self.stats(42_000_000, 10_000_000)

        for _ in range(2):
            self.assertEqual(
                detect_congested_links(
                    self.topology,
                    stats,
                    self.history,
                    capacity_bps=50_000_000,
                ),
                [],
            )

        result = detect_congested_links(
            self.topology,
            stats,
            self.history,
            capacity_bps=50_000_000,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["utilization_percent"], 84.0)

    def test_invalid_capacity_rejected(self):
        for capacity in (0, -1):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    detect_congested_links(
                        self.topology,
                        self.stats(0, 0),
                        {},
                        capacity_bps=capacity,
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
