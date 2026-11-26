"""Real subprocess MCP handshake and tool calls, backed by the local API fixture."""

import asyncio
import runpy
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

TOOLS = {
    "check_connection",
    "list_workspaces",
    "list_item_types",
    "list_items",
    "search_items",
    "read_item",
    "get_authoring_guidance",
    "preview_item",
    "create_item",
    "update_item",
}


def test_stdio_protocol_and_read_only_tools(api, tmp_path):
    async def scenario():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "scenari_mcp"],
            cwd=tmp_path,
            env={
                "SCENARI_URL": api.settings.url,
                "SCENARI_USERNAME": api.settings.username,
                "SCENARI_PASSWORD": api.settings.password,
            },
        )
        async with Client(params, read_timeout_seconds=10) as client:
            tools = (await client.list_tools()).tools
            assert {t.name for t in tools} == TOOLS
            assert all(
                t.annotations.read_only_hint
                for t in tools
                if t.name not in {"create_item", "update_item"}
            )
            assert all(
                not t.annotations.read_only_hint
                for t in tools
                if t.name in {"create_item", "update_item"}
            )
            # Guidance is available over the wire without any Scenari API requests.
            assert client.instructions
            assert "scenari://authoring/overview" in client.instructions
            guidance = await client.call_tool("get_authoring_guidance", {"section": "all"})
            assert not guidance.is_error
            documents = guidance.structured_content["documents"]
            assert len(documents) == 4
            resources = (await client.list_resources()).resources
            assert {str(r.uri) for r in resources} == {d["uri"] for d in documents}
            for doc in documents:
                result = await client.read_resource(doc["uri"])
                assert result.contents[0].text == doc["content"]
            bad = await client.call_tool("get_authoring_guidance", {"section": "../../.env"})
            assert bad.is_error
            assert not api.requests
            draft = {
                "kind": "procedure",
                "title": "Example process",
                "steps": [
                    {
                        "instruction": "Inspect",
                        "details": [{"paragraphs": ["Inspect the provided copy."]}],
                    }
                ],
            }
            preview = await client.call_tool(
                "preview_item", {"workspace": "dokiel-test", "item": draft}
            )
            assert not preview.is_error, preview.content
            assert preview.structured_content["model"] == "dk_stepList"
            disabled = await client.call_tool(
                "create_item", {"workspace": "dokiel-test", "path": "/new.unit", "item": draft}
            )
            assert disabled.is_error
            assert "WRITES_DISABLED" in disabled.content[0].text
            for name, arguments in [
                ("check_connection", {}),
                ("list_workspaces", {}),
                ("list_item_types", {"workspace": "dokiel-test"}),
                ("list_items", {"workspace": "dokiel-test"}),
                ("search_items", {"workspace": "dokiel-test", "query": 'A & "B"'}),
                ("read_item", {"workspace": "dokiel-test", "reference": "/topic.unit"}),
            ]:
                result = await client.call_tool(name, arguments)
                assert not result.is_error, result.content
                assert isinstance(result.structured_content, dict)
            invalid = await client.call_tool(
                "search_items", {"workspace": "dokiel-test", "limit": 101}
            )
            assert invalid.is_error
            missing = await client.call_tool(
                "read_item", {"workspace": "dokiel-test", "reference": "/missing.unit"}
            )
            assert missing.is_error
            text = " ".join(block.text for block in missing.content)
            assert "NOT_FOUND" in text
            assert "private" not in text

    asyncio.run(scenario())
    assert all(method == "GET" for method, _ in api.requests)


def test_enabled_full_authoring_workflow_over_stdio(api, tmp_path):
    # Reuse the live workflow against a local fixture so all typed kinds, linked item
    # assembly, XML creation and stale-update protection stay covered without live writes.
    script = Path(__file__).resolve().parents[1] / "scripts/write_smoke_test.py"
    smoke = runpy.run_path(str(script))["smoke"]
    env_file = tmp_path / "test.env"
    env_file.write_text(
        f"SCENARI_URL={api.settings.url}\nSCENARI_USERNAME=author\nSCENARI_PASSWORD=test-secret\n"
    )
    api.resolve_refs = True
    result = asyncio.run(smoke(env_file, "dokiel-test", "/Folder"))
    assert result["passed"] and result["items_created"] == 13
    assert result["update"]["sha256"] != result["update"]["previous_sha256"]
    assert result["collision_and_stale_update_rejected"]
    assert sum(method == "PUT" for method, _ in api.requests) == 14
