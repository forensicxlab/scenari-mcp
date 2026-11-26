"""Opt-in, read-only live verification through a real stdio MCP subprocess."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def smoke(env_file: Path | None, workspace: str | None) -> dict:
    args = ["-m", "scenari_mcp"]
    if env_file:
        args += ["--env-file", str(env_file.resolve())]
    params = StdioServerParameters(
        command=sys.executable,
        args=args,
        env={key: value for key, value in os.environ.items() if key.startswith("SCENARI_")},
    )
    checked = []
    async with Client(params, read_timeout_seconds=60) as client:

        async def call(name: str, arguments: dict | None = None) -> dict:
            result = await client.call_tool(name, arguments or {})
            if result.is_error:
                text = " ".join(getattr(block, "text", "") for block in result.content)
                raise RuntimeError(f"{name} failed: {text}")
            if not isinstance(result.structured_content, dict):
                raise RuntimeError(f"{name} did not return structured data.")
            checked.append(name)
            return result.structured_content

        tools = (await client.list_tools()).tools
        writes = {"create_item", "update_item"}
        if not all(
            tool.annotations and tool.annotations.read_only_hint == (tool.name not in writes)
            for tool in tools
        ):
            raise RuntimeError("Tools must accurately declare their write capabilities.")
        if not client.instructions:
            raise RuntimeError("Initialization must provide the core course-design instructions.")
        guidance = await call("get_authoring_guidance", {"section": "all"})
        if len(guidance["documents"]) != 4:
            raise RuntimeError("The complete authoring skill must be available.")
        resources = (await client.list_resources()).resources
        if len(resources) != 4:
            raise RuntimeError("The four authoring resources must be discoverable.")
        for resource in resources:
            await client.read_resource(str(resource.uri))
        connection = await call("check_connection")
        workspaces = (await call("list_workspaces"))["workspaces"]
        if workspace is None:
            if len(workspaces) != 1:
                raise RuntimeError("Pass --workspace with an exact code from list_workspaces.")
            workspace = workspaces[0]["code"]
        catalog = await call("list_item_types", {"workspace": workspace})
        root = await call("list_items", {"workspace": workspace})
        # Find an existing XML item without relying on this instance's course paths.
        matches = await call(
            "search_items", {"workspace": workspace, "model": "dk_stepList", "limit": 1}
        )
        if not matches["items"]:
            matches = await call(
                "search_items", {"workspace": workspace, "model": "dk_module", "limit": 1}
            )
        if not matches["items"]:
            raise RuntimeError("Discovery passed; add a procedure or module to verify read_item.")
        item = await call(
            "read_item", {"workspace": workspace, "reference": matches["items"][0]["path"]}
        )
        return {
            "passed": True,
            "server_version": connection["server"].get("serverVersion"),
            "workspace": catalog["workspace"]["title"],
            "dokiel_version": catalog["workspace"]["model"].get("version"),
            "dokiel_item_types": catalog["count"],
            "root_entries": root["total"],
            "read_item_bytes": item["bytes"],
            "verified_tools": sorted(set(checked)),
            "verified_authoring_resources": len(resources),
            "server_instructions_received": True,
            "read_only": True,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--workspace", help="Exact workspace code; optional when there is one Dokiel workspace."
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(smoke(args.env_file, args.workspace)), indent=2))


if __name__ == "__main__":
    main()
