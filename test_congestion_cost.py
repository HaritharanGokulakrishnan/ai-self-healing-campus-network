from controller_client import send
import time

link = ("s1", "s2")

try:
    print("\n1. Checking controller status...")
    print(send({"cmd": "STATUS"}))

    print("\n2. Raising cost of s1-s2 to 100...")
    result = send({
        "cmd": "SET_LINK_COST",
        "a": link[0],
        "b": link[1],
        "cost": 100
    })
    print("Controller response:", result)

    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError("Controller rejected the cost change")

    print("\n3. Verifying the cost override...")
    status = send({"cmd": "STATUS"})
    print("Controller status:", status)

    overrides = status.get("cost_overrides", [])
    found = any(
        {item.get("a"), item.get("b")} == set(link)
        and item.get("cost") == 100
        for item in overrides
    )

    print("Cost override confirmed:", found)

finally:
    print("\n4. Clearing the temporary cost override...")
    try:
        print(send({
            "cmd": "CLEAR_LINK_COST",
            "a": link[0],
            "b": link[1]
        }))
    except Exception as exc:
        print("WARNING: Could not clear override:", exc)

print("\nController cost test completed.")
