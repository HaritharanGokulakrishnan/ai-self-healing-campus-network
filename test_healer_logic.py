import contextlib
import io
from unittest.mock import patch

import healer


def run_test(name, test_function):
    test_function()
    print(f"PASS: {name}")


def clear_cs_results():
    return [
        ("h_cs", "h_lib", "link_failure"),
        ("h_cs", "h_admin", "link_failure"),
        ("h_cs", "h_hos", "link_failure"),
        ("h_lib", "h_admin", "normal"),
    ]


def test_clear_cs_failure():
    healed = set()

    with patch.object(healer, "send", return_value={"ok": True}) as mock_send:
        building = healer.heal_if_needed(clear_cs_results(), healed)

    assert building == "CS"
    assert healed == {("s1", "s3")}
    mock_send.assert_called_once_with(
        {"cmd": "FAIL_LINK", "a": "s1", "b": "s3"}
    )


def test_insufficient_evidence():
    healed = set()

    with patch.object(healer, "send") as mock_send:
        building = healer.heal_if_needed(
            [("h_cs", "h_lib", "link_failure")], healed
        )

    assert building is None
    assert not healed
    mock_send.assert_not_called()


def test_tied_candidates():
    results = [
        ("h_cs", "h_lib", "link_failure"),
        ("h_admin", "h_hos", "link_failure"),
        ("h_cs", "h_admin", "link_failure"),
        ("h_lib", "h_hos", "link_failure"),
    ]
    healed = set()

    with patch.object(healer, "send") as mock_send:
        building = healer.heal_if_needed(results, healed)

    assert building is None
    assert not healed
    mock_send.assert_not_called()


def test_congestion_alert_only():
    results = [
        ("h_lib", "h_cs", "congestion"),
        ("h_lib", "h_admin", "congestion"),
    ]
    healed = set()
    output = io.StringIO()

    with patch.object(healer, "send") as mock_send:
        with contextlib.redirect_stdout(output):
            building = healer.heal_if_needed(results, healed)

    assert building is None
    assert not healed
    mock_send.assert_not_called()
    assert "no automatic action yet" in output.getvalue()


def test_duplicate_healing_not_resent():
    healed = {("s1", "s3")}

    with patch.object(healer, "send") as mock_send:
        building = healer.heal_if_needed(clear_cs_results(), healed)

    assert building == "CS"
    mock_send.assert_not_called()


def test_rejected_command_not_recorded():
    healed = set()

    with patch.object(
        healer, "send", return_value={"ok": False, "error": "rejected"}
    ):
        building = healer.heal_if_needed(clear_cs_results(), healed)

    assert building is None
    assert not healed


def test_connection_error_not_recorded():
    healed = set()

    with patch.object(
        healer, "send", side_effect=ConnectionError("controller unavailable")
    ):
        building = healer.heal_if_needed(clear_cs_results(), healed)

    assert building is None
    assert not healed


def test_malformed_response_not_recorded():
    healed = set()

    with patch.object(healer, "send", return_value=None):
        building = healer.heal_if_needed(clear_cs_results(), healed)

    assert building is None
    assert not healed


def test_congestion_cost_override_acknowledged():
    response = {"ok": True}
    with patch.object(healer, "send", return_value=response) as mock_send:
        result = healer.send({
            "cmd": "SET_LINK_COST",
            "a": "s1",
            "b": "s3",
            "cost": 100,
        })

    assert result.get("ok") is True
    mock_send.assert_called_once_with({
        "cmd": "SET_LINK_COST",
        "a": "s1",
        "b": "s3",
        "cost": 100,
    })


def test_congestion_cost_override_rejected():
    with patch.object(
        healer, "send",
        return_value={"ok": False, "error": "rejected"},
    ) as mock_send:
        response = healer.send({
            "cmd": "SET_LINK_COST",
            "a": "s1",
            "b": "s3",
            "cost": 100,
        })

    assert response.get("ok") is False
    mock_send.assert_called_once()


def test_congestion_cost_override_cleared():
    with patch.object(healer, "send", return_value={"ok": True}) as mock_send:
        response = healer.send({
            "cmd": "CLEAR_LINK_COST",
            "a": "s1",
            "b": "s3",
        })

    assert response.get("ok") is True
    mock_send.assert_called_once_with({
        "cmd": "CLEAR_LINK_COST",
        "a": "s1",
        "b": "s3",
    })


def test_mitigate_congestion_acknowledged():
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


def test_mitigate_congestion_duplicate():
    mitigated = {("s1", "s3")}
    with patch.object(healer, "send") as mock_send:
        result = healer.mitigate_congestion(("s1", "s3"), mitigated)

    assert result is True
    mock_send.assert_not_called()


def test_mitigate_congestion_rejected():
    mitigated = set()
    with patch.object(
        healer, "send",
        return_value={"ok": False, "error": "rejected"},
    ):
        result = healer.mitigate_congestion(("s1", "s3"), mitigated)

    assert result is False
    assert not mitigated


if __name__ == "__main__":
    tests = [
        ("Clear CS failure with acknowledgement", test_clear_cs_failure),
        ("Insufficient evidence", test_insufficient_evidence),
        ("Tied candidates", test_tied_candidates),
        ("Congestion alert only", test_congestion_alert_only),
        ("Duplicate healing protection", test_duplicate_healing_not_resent),
        ("Rejected command is not recorded", test_rejected_command_not_recorded),
        ("Connection failure is not recorded", test_connection_error_not_recorded),
        ("Malformed response is not recorded", test_malformed_response_not_recorded),
        ("Congestion cost override acknowledged", test_congestion_cost_override_acknowledged),
        ("Congestion cost override rejected", test_congestion_cost_override_rejected),
        ("Congestion cost override cleared", test_congestion_cost_override_cleared),
        ("Mitigation acknowledgement", test_mitigate_congestion_acknowledged),
        ("Mitigation duplicate protection", test_mitigate_congestion_duplicate),
        ("Mitigation rejection", test_mitigate_congestion_rejected),
    ]

    for name, test_function in tests:
        run_test(name, test_function)

    print("\\nALL HEALER LOGIC TESTS PASSED")
