from unittest.mock import patch
import healer

def test_explicit_link_mitigation():
    mitigated = set()
    with patch.object(healer, "send", return_value={"ok": True}) as mock_send:
        result = healer.mitigate_congestion(("s1", "s3"), mitigated)

    assert result is True
    assert mitigated == {("s1", "s3")}
    mock_send.assert_called_once_with({
        "cmd": "SET_LINK_COST",
        "a": "s1",
        "b": "s3",
        "cost": 100,
    })
    print("PASS: Explicit-link congestion mitigation workflow")

if __name__ == "__main__":
    test_explicit_link_mitigation()
