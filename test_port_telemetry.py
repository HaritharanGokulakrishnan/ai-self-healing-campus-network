import unittest
from port_telemetry import calculate_port_rates, utilization


class PortTelemetryTests(unittest.TestCase):
    def test_rate_calculation(self):
        previous = {("s1", 2): {"tx_bytes": 1000, "rx_bytes": 500}}
        current = {("s1", 2): {"tx_bytes": 2000, "rx_bytes": 1500}}
        rates = calculate_port_rates(previous, current, 2)
        self.assertEqual(rates[("s1", 2)]["tx_bps"], 4000)
        self.assertEqual(rates[("s1", 2)]["rx_bps"], 4000)

    def test_first_sample_is_skipped(self):
        current = {("s1", 2): {"tx_bytes": 2000, "rx_bytes": 1500}}
        self.assertEqual(calculate_port_rates({}, current, 1), {})

    def test_counter_reset_is_skipped(self):
        previous = {("s1", 2): {"tx_bytes": 2000, "rx_bytes": 1500}}
        current = {("s1", 2): {"tx_bytes": 100, "rx_bytes": 2000}}
        self.assertEqual(calculate_port_rates(previous, current, 1), {})

    def test_utilization(self):
        self.assertAlmostEqual(utilization(800_000_000, 1_000_000_000), 80.0)

    def test_invalid_elapsed(self):
        with self.assertRaises(ValueError):
            calculate_port_rates({}, {}, 0)

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            utilization(100, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
