"""Tests for integration intent — envelope, Anthropic export, server contract."""
from gate_sdk import GateClient
from gate_sdk.server_client import ServerEndpoints, tools_to_server_payload, filter_result_from_server


def test_export_anthropic():
    client = GateClient(mode=0.0)
    client.add_tool("search", "read_only", description="Search docs")
    tools = client.export_anthropic()
    assert len(tools) == 1
    assert tools[0]["name"] == "search"
    assert "input_schema" in tools[0]


def test_export_anthropic_suppresses():
    client = GateClient(mode=0.9)
    client.add_tool("search", "read_only")
    client.add_tool("deploy", "high_impact")
    tools = client.export_anthropic()
    assert len(tools) == 1
    assert tools[0]["name"] == "search"


def test_authorize_visible_tool():
    client = GateClient(mode=0.0)
    client.add_tool("read_file", "read_only", description="Read")
    env = client.authorize("read_file", signing_key="test-key", context_id="sess1")
    assert env.tool_name == "read_file"
    assert env.signature != ""
    assert client.verify(env, "test-key")


def test_authorize_suppressed_tool_raises():
    client = GateClient(mode=0.9)
    client.add_tool("deploy", "high_impact")
    try:
        client.authorize("deploy", signing_key="test-key")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "suppressed" in str(e)


def test_authorize_crisis_tightens_envelope():
    client = GateClient(mode=0.0)
    client.add_tool("read_file", "read_only")

    env_normal = client.authorize("read_file", signing_key="k", mode=0.1)
    env_crisis = client.authorize("read_file", signing_key="k", mode=0.8)

    assert env_normal.budget_seconds == 30
    assert env_normal.execution_mode == "standard"
    assert env_crisis.budget_seconds == 7
    assert env_crisis.execution_mode == "minimal"


def test_server_endpoints():
    ep = ServerEndpoints(base_url="http://gate:8900")
    assert ep.filter == "http://gate:8900/api/v1/tools/filter"
    assert ep.envelope == "http://gate:8900/api/v1/envelope/build"
    assert ep.health == "http://gate:8900/api/v1/health"
    assert ep.mode_history == "http://gate:8900/api/v1/mode/history"


def test_tools_to_server_payload():
    payload = tools_to_server_payload([
        {"name": "a", "execution_class": "read_only", "description": "tool a"},
    ])
    assert payload == {"tools": [
        {"name": "a", "execution_class": "read_only", "description": "tool a", "inputs": {}},
    ]}


def test_filter_result_from_server():
    raw = {"visible": [{"name": "a"}], "suppressed": [], "mode": 0.2, "mode_zone": "normal"}
    parsed = filter_result_from_server(raw)
    assert parsed["mode_zone"] == "normal"
    assert len(parsed["visible"]) == 1


def test_policy_middleware_refilters_at_stricter_mode():
    """PolicyMiddleware re-filters when policy demands stricter mode."""
    from gate_sdk.policy import PolicyMiddleware

    class StrictPolicy:
        def evaluate(self, context):
            return 0.8  # always crisis

        def name(self):
            return "strict-test"

    client = GateClient(mode=0.0)
    client.add_tool("read_file", "read_only")
    client.add_tool("deploy", "high_impact")
    client.add_tool("write_file", "state_mutation")

    middleware = PolicyMiddleware(StrictPolicy())
    client.use(middleware.hook)

    result = client.filter()
    # Policy says 0.8 (crisis) which is stricter than ambient 0.0
    # high_impact and state_mutation should be suppressed
    assert "read_file" in result.visible_names
    assert "deploy" in result.suppressed_names
    assert "write_file" in result.suppressed_names
    assert result.mode_zone == "crisis"


def test_policy_middleware_passthrough_when_lax():
    """PolicyMiddleware passes through when policy is less strict than ambient."""
    from gate_sdk.policy import PolicyMiddleware

    class LaxPolicy:
        def evaluate(self, context):
            return 0.0  # always calm

        def name(self):
            return "lax-test"

    client = GateClient(mode=0.5)
    client.add_tool("read_file", "read_only")
    client.add_tool("deploy", "high_impact")

    middleware = PolicyMiddleware(LaxPolicy())
    client.use(middleware.hook)

    result = client.filter()
    # Ambient mode 0.5 is stricter than policy 0.0, so no re-filtering
    # deploy should already be suppressed at 0.5 (>0.35 threshold for high_impact)
    assert "deploy" in result.suppressed_names
    assert result.mode == 0.5
