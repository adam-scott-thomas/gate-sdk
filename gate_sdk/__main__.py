"""CLI demo — run `python -m gate_sdk` for a quick Gate demo.

Shows how the SDK works across all three mode zones with a handful of tools.
"""
import sys
from gate_sdk import GateClient


def main() -> None:
    client = GateClient()
    client.add_tool("read_docs", "read_only", description="Read documentation")
    client.add_tool("analyze_risk", "advisory", description="Analyze risk score")
    client.add_tool("send_alert", "external_action", description="Send Slack alert")
    client.add_tool("update_config", "state_mutation", description="Update system config")
    client.add_tool("deploy_prod", "high_impact", description="Deploy to production")

    suppressed_log: list[str] = []

    def track_suppression(tool, mode):
        suppressed_log.append(tool.name)

    client.on_suppress(track_suppression)

    zones = [
        ("normal",   0.2),
        ("elevated", 0.5),
        ("crisis",   0.9),
    ]

    print("Maelstrom Gate SDK Demo")
    print("=" * 50)
    print(f"Registered tools: {[t.name for t in client.tools]}")
    print()

    for zone_name, mode in zones:
        suppressed_log.clear()
        result = client.filter(mode)
        print(f"--- {zone_name.upper()} (mode={mode}) ---")
        print(f"  Visible:    {result.visible_names}")
        print(f"  Suppressed: {result.suppressed_names}")
        print(f"  Zone:       {result.mode_status}")
        print()

    # Context manager demo
    print("--- CONTEXT MANAGER OVERRIDE ---")
    client.mode = 0.0
    print(f"  Default mode: {client.mode}")
    with client.override_mode(0.9):
        r = client.filter()
        print(f"  Inside override (0.9): visible={r.visible_names}")
    r = client.filter()
    print(f"  After override: visible={r.visible_names}")
    print()

    # OpenAI export demo
    print("--- OPENAI EXPORT (mode=0.0) ---")
    openai_tools = client.export_openai(mode=0.0)
    for t in openai_tools:
        print(f"  {t['function']['name']}: {t['function']['description']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
