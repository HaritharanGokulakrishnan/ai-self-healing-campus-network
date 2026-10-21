import unittest
from unittest.mock import patch

import congestion_healer


class CongestionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.result = {
            "congested_links": [
                {
                    "a": "s1",
                    "b": "s3",
                    "utilization_percent": 85.0,
                    "rate_bps": 850_000_000,
                }
            ]
        }

    def test_read_only_does_not_mitigate(self):
        with patch.object(
            congestion_healer, "mitigate_congestion"
        ) as mock_mitigate:
            detected = congestion_healer.process_congestion_result(
                self.result, mitigate=False
            )

        self.assertEqual(len(detected), 1)
        mock_mitigate.assert_not_called()

    def test_mitigation_requests_targeted_link(self):
        mitigated = set()
        with patch.object(
            congestion_healer, "mitigate_congestion", return_value=True
        ) as mock_mitigate:
            detected = congestion_healer.process_congestion_result(
                self.result,
                mitigate=True,
                mitigated=mitigated,
                cost=100,
                target_link=("s1", "s3"),
            )

        self.assertEqual(len(detected), 1)
        mock_mitigate.assert_called_once_with(
            ("s1", "s3"), mitigated, cost=100
        )

    def test_non_targeted_link_is_not_mitigated(self):
        mitigated = set()
        with patch.object(
            congestion_healer, "mitigate_congestion"
        ) as mock_mitigate:
            congestion_healer.process_congestion_result(
                self.result,
                mitigate=True,
                mitigated=mitigated,
                cost=100,
                target_link=("s1", "s2"),
            )

        mock_mitigate.assert_not_called()

    def test_no_detected_links_means_no_mitigation(self):
        with patch.object(
            congestion_healer, "mitigate_congestion"
        ) as mock_mitigate:
            congestion_healer.process_congestion_result(
                {"congested_links": []},
                mitigate=True,
                target_link=("s1", "s3"),
            )

        mock_mitigate.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
