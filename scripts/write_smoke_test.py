"""Opt-in live MCP writes in a unique new folder; never updates pre-existing course items."""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from mcp import Client
from mcp.client.stdio import StdioServerParameters


def examples(folder):
    def block(text, type="information"):
        return {"type": type, "paragraphs": [text]}

    def ref(name):
        return f"{folder}/{name}"

    return [
        (
            "definition.ref",
            {
                "kind": "definition",
                "term": "Steeping",
                "synonyms": ["Infusing"],
                "paragraphs": ["Leaving tea leaves in water to extract flavour."],
            },
        ),
        (
            "source.ref",
            {
                "kind": "bibliography",
                "identifier": "Test source",
                "citation": "Synthetic reference used solely for MCP integration testing.",
            },
        ),
        (
            "website.url",
            {"kind": "web_reference", "title": "Example reference", "url": "https://example.org/"},
        ),
        (
            "concept.unit",
            {
                "kind": "concept",
                "title": "MCP write test: steeping",
                "definition": ref("definition.ref"),
                "blocks": [
                    block("Use the tea packet instructions."),
                    block("Choose a timer.", "tip"),
                    block("Different teas vary.", "remark"),
                    block("Hot water can burn.", "warning"),
                ],
            },
        ),
        (
            "process.unit",
            {
                "kind": "procedure",
                "title": "MCP write test: brew tea",
                "introduction": [block("Prepare a cup using the packet instructions.")],
                "prerequisites": [block("A suitable cup, tea, water and timer.")],
                "steps": [
                    {
                        "instruction": "Steep the tea.",
                        "details": [block("Follow the packet temperature and time.")],
                        "result": [block("Tea brewed for the measured time.")],
                    }
                ],
                "result": [block("Remove the leaves and allow the tea to cool.")],
                "comments": [block("Record the steeping time.", "tip")],
            },
        ),
        (
            "theory.unit",
            {
                "kind": "theory",
                "title": "MCP write test: tea method",
                "blocks": [block("Read these references before practicing.")],
                "links": [
                    {"type": "concept", "reference": ref("concept.unit")},
                    {"type": "procedure", "reference": ref("process.unit")},
                ],
            },
        ),
        (
            "practice.unit",
            {
                "kind": "guided_exercise",
                "title": "MCP write test: practical activity",
                "duration": "5 minutes",
                "statement": [block("Brew a cup following your tea packet. Record time.")],
                "questions": [
                    {
                        "prompt": "What time did you use, and why?",
                        "solution": [
                            block(
                                "Report your measured time and compare it "
                                "with the packet recommendation."
                            )
                        ],
                        "hints": ["Look at the packet before choosing a time."],
                    }
                ],
                "solution": [block("Evaluate the result before your next cup.")],
            },
        ),
        (
            "check.quiz",
            {
                "kind": "single_choice_quiz",
                "question": "When should you remove the leaves?",
                "choices": [
                    {
                        "label": "At the chosen packet steeping time.",
                        "explanation": "This controls the duration.",
                    },
                    {
                        "label": "Leave them indefinitely.",
                        "explanation": "Steeping would continue.",
                    },
                ],
                "correct_choice": 1,
                "feedback_right": "Correct; use the measured time.",
                "feedback_wrong": "Review the recommended steeping time.",
            },
        ),
        (
            "assessment.scen",
            {
                "kind": "assessment",
                "title": "MCP write test: knowledge check",
                "quizzes": [ref("check.quiz")],
            },
        ),
        (
            "module.scen",
            {
                "kind": "module",
                "title": "MCP write test: tea module",
                "objectives": [
                    "Apply the packet instructions to brew a cup and justify "
                    "the selected steeping time."
                ],
                "parts": [
                    {"type": "theory", "reference": ref("theory.unit")},
                    {"type": "guided_exercise", "reference": ref("practice.unit")},
                ],
            },
        ),
        (
            "tutorial.scen",
            {
                "kind": "tutorial",
                "title": "MCP write test: tea tutorial",
                "modules": [ref("module.scen")],
                "assessment": ref("assessment.scen"),
            },
        ),
        ("course.pub", {"kind": "publication", "content": ref("tutorial.scen")}),
    ]


async def smoke(env_file, workspace, parent):
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    folder = f"{parent.rstrip('/')}/MCP_Write_Test_{stamp}_{uuid4().hex[:6]}"
    args = ["-m", "scenari_mcp"]
    if env_file:
        args += ["--env-file", str(env_file.resolve())]
    env = {k: v for k, v in os.environ.items() if k.startswith("SCENARI_")}
    env["SCENARI_ENABLE_WRITES"] = "true"
    params = StdioServerParameters(command=sys.executable, args=args, env=env)
    receipts = []
    async with Client(params, read_timeout_seconds=120) as client:

        async def call(name, arguments):
            result = await client.call_tool(name, arguments)
            if result.is_error:
                raise RuntimeError(
                    f"{name}: " + " ".join(getattr(b, "text", "") for b in result.content)
                )
            return result.structured_content

        if workspace is None:
            workspaces = (await call("list_workspaces", {}))["workspaces"]
            if len(workspaces) != 1:
                raise RuntimeError("Specify --workspace with an exact code.")
            workspace = workspaces[0]["code"]
        items = examples(folder)
        for i, (filename, item) in enumerate(items):
            preview = await call("preview_item", {"workspace": workspace, "item": item})
            if preview["write_applied"]:
                raise RuntimeError("Preview must not write.")
            result = await call(
                "create_item",
                {
                    "workspace": workspace,
                    "path": f"{folder}/{filename}",
                    "item": item,
                    "create_parents": i == 0,
                },
            )
            print(
                json.dumps(
                    {
                        "path": result["reference"],
                        "status": result["status"],
                        "verified": result["verified"],
                    }
                ),
                file=sys.stderr,
                flush=True,
            )
            if not result["verified"]:
                raise RuntimeError(f"Write verification failed: {result}")
            receipts.append(
                {
                    "reference": result["reference"],
                    "model": result["model"],
                    "status": result["status"],
                    "sha256": result["item"]["sha256"],
                }
            )
        # Advanced XML create, then structured update with a digest of an item created above.
        process_path = f"{folder}/process.unit"
        original = await call("read_item", {"workspace": workspace, "reference": process_path})
        raw = await call(
            "create_item",
            {
                "workspace": workspace,
                "path": f"{folder}/advanced.unit",
                "item": {"kind": "xml", "model": "dk_stepList", "xml": original["xml"]},
            },
        )
        if not raw["verified"]:
            raise RuntimeError(f"Advanced XML verification failed: {raw}")
        replacement = next(item for filename, item in items if filename == "process.unit").copy()
        replacement["title"] += " (updated)"
        updated = await call(
            "update_item",
            {
                "workspace": workspace,
                "reference": process_path,
                "expected_sha256": original["sha256"],
                "item": replacement,
            },
        )
        if not updated["verified"] or updated["previous_item"]["sha256"] != original["sha256"]:
            raise RuntimeError(f"Update verification failed: {updated}")
        # Verify these guards through the real protocol, with no intended writes.
        for name, arguments, code in [
            (
                "create_item",
                {"workspace": workspace, "path": process_path, "item": replacement},
                "ALREADY_EXISTS",
            ),
            (
                "update_item",
                {
                    "workspace": workspace,
                    "reference": process_path,
                    "expected_sha256": original["sha256"],
                    "item": replacement,
                },
                "CONFLICT",
            ),
        ]:
            rejected = await client.call_tool(name, arguments)
            if not rejected.is_error or code not in rejected.content[0].text:
                raise RuntimeError(f"{code} protection failed.")
        receipts.append(
            {
                "reference": raw["reference"],
                "model": raw["model"],
                "status": raw["status"],
                "sha256": raw["item"]["sha256"],
            }
        )
    return {
        "passed": True,
        "workspace": workspace,
        "folder": folder,
        "items_created": len(receipts),
        "update_verified": True,
        "update": {
            "reference": process_path,
            "previous_sha256": original["sha256"],
            "sha256": updated["item"]["sha256"],
        },
        "collision_and_stale_update_rejected": True,
        "items": receipts,
        "generated_output": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--workspace")
    parser.add_argument("--parent", default="/x_Playground")
    parser.add_argument(
        "--apply", action="store_true", help="Enable writes in this test subprocess."
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if not args.apply:
        parser.error("Pass --apply to create test items in a unique new folder.")
    result = asyncio.run(smoke(args.env_file, args.workspace, args.parent))
    output = json.dumps(result, indent=2) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(output)
    print(output)


if __name__ == "__main__":
    main()
