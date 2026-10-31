"""
Test file for the D&D MCP Server (FastMCP 2.8.0+ compliant).
"""

from pathlib import Path

import pytest
from gamemaster_mcp.main import mcp
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore


def test_mcp_server_initialization():
    """Test that the FastMCP server initializes correctly."""
    assert mcp.name == "gamemaster-mcp"


def test_tool_descriptions_are_concise_and_distinguish_related_tools():
    """Every registered tool should have a concise, useful description."""
    tools = mcp._tool_manager._tools

    assert tools
    for tool in tools.values():
        assert tool.description
        assert len(tool.description.split(". ")) <= 5

    assert "player-facing" in tools["create_npc"].description
    assert "DM-only" in tools["create_npc"].description
    assert "DM-only" in tools["get_npc"].description
    assert "shared across campaigns" in tools["add_event"].description
    assert "campaign session" in tools["add_session_note"].description


def test_storage_initialization():
    """Test that storage initializes correctly."""
    storage = DnDStorage("test_data")
    assert storage.data_dir.name == "test_data"


def test_character_model():
    """Test character model creation."""
    character = Character(
        name="Test Character",
        character_class=CharacterClass(name="Fighter", level=1),
        race=Race(name="Human"),
        abilities={
            "strength": AbilityScore(score=15),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=13),
            "intelligence": AbilityScore(score=12),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=8),
        }
    )
    
    assert character.name == "Test Character"
    assert character.character_class.name == "Fighter"
    assert character.character_class.level == 1
    assert character.abilities["strength"].score == 15
    assert character.abilities["strength"].mod == 2  # (15-10)//2 = 2


def test_ability_score_modifier():
    """Test ability score modifier calculation."""
    # Test various scores
    test_cases = [
        (1, -5),    # Score 1 -> modifier -5
        (8, -1),    # Score 8 -> modifier -1  
        (10, 0),    # Score 10 -> modifier 0
        (11, 0),    # Score 11 -> modifier 0
        (12, 1),    # Score 12 -> modifier 1
        (15, 2),    # Score 15 -> modifier 2
        (20, 5),    # Score 20 -> modifier 5
        (30, 10),   # Score 30 -> modifier 10
    ]
    
    for score, expected_modifier in test_cases:
        ability = AbilityScore(score=score)
        assert ability.mod == expected_modifier, f"Score {score} should have modifier {expected_modifier}, got {ability.mod}"


def test_health_endpoint_and_bearer_auth():
    """Test /health is open and the MCP path honours the optional bearer token."""
    from starlette.middleware import Middleware
    from starlette.testclient import TestClient

    from gamemaster_mcp.main import BearerAuthMiddleware, mcp

    app = mcp.http_app(middleware=[Middleware(BearerAuthMiddleware, token="s3cret")])
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert client.get("/mcp").status_code == 401
        assert client.get("/mcp", headers={"Authorization": "******"}).status_code == 401
        assert client.get("/mcp", headers={"Authorization": "Bearer " + "s3cret"}).status_code != 401


def _parse_mcp_response(response):
    """Parse a Streamable HTTP JSON or SSE JSON-RPC body."""
    import json

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


def test_vercel_asgi_entrypoint_exports_app():
    """Vercel loads src/main.py and requires a top-level ASGI ``app``."""
    import importlib

    module = importlib.import_module("main")
    assert hasattr(module, "app")
    assert callable(module.app)


def test_resolve_storage_dir_uses_tmp_on_vercel(monkeypatch, tmp_path):
    """On Vercel, unset GAMEMASTER_STORAGE_DIR should fall back to /tmp/gamemaster."""
    from gamemaster_mcp.main import resolve_storage_dir

    monkeypatch.delenv("GAMEMASTER_STORAGE_DIR", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    assert resolve_storage_dir() == Path("/tmp/gamemaster")

    monkeypatch.setenv("GAMEMASTER_STORAGE_DIR", str(tmp_path / "custom"))
    assert resolve_storage_dir() == (tmp_path / "custom").resolve()


def test_streamable_http_initialize_and_tools_list():
    """Stateless Streamable HTTP accepts initialize and tools/list (Vercel mode)."""
    from starlette.testclient import TestClient

    from gamemaster_mcp.main import create_http_app

    app = create_http_app(path="/mcp", stateless_http=True)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"

        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        }
        init_resp = client.post("/mcp/", json=init, headers=headers)
        assert init_resp.status_code == 200
        init_body = _parse_mcp_response(init_resp)
        assert init_body["result"]["serverInfo"]["name"] == "gamemaster-mcp"

        client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=headers,
        )

        tools_resp = client.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=headers,
        )
        assert tools_resp.status_code == 200
        tools_body = _parse_mcp_response(tools_resp)
        names = {tool["name"] for tool in tools_body["result"]["tools"]}
        assert "list_campaigns" in names
        assert "roll_dice" in names
        assert len(names) >= 10


if __name__ == "__main__":
    pytest.main([__file__])
