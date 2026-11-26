import json
import os
import re
import runpy
import subprocess
import sys
import zipfile
from pathlib import Path

from scenari_mcp.guidance import DOCUMENTS, get_guidance, read_section, skill_root

ROOT = Path(__file__).resolve().parents[1]


def test_guidance_is_complete_and_local_links_resolve_to_resources():
    result = get_guidance("all")
    assert len(result["documents"]) == 4
    uris = {doc["uri"] for doc in result["documents"]}
    for section, (source, _) in DOCUMENTS.items():
        assert skill_root().joinpath(source).is_file()
        text = read_section(section)
        links = re.findall(r"\]\(([^)]+)\)", text)
        assert all("://" in link for link in links)
        assert all(link in uris for link in links if link.startswith("scenari://"))


def test_plugin_zip_excludes_secrets_and_preserves_skill_files(tmp_path):
    build = runpy.run_path(str(ROOT / "scripts/build_plugin.py"))["build_plugin"]
    archive = build(ROOT, tmp_path / "plugin.zip")
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
        assert {"plugin.json", "mcp.json", "scripts/run_plugin.py", "uv.lock"} <= names
        assert "skills/scenari-forensics-course-design/SKILL.md" in names
        assert len([name for name in names if "/references/" in name]) == 3
        assert ".env" not in names
        assert ".env.example" in names
        assert not any(
            part in {".venv", ".tools", ".cache", "examples", "dist", ".git", "__pycache__"}
            for name in names
            for part in Path(name).parts
        )
        manifest = json.loads(z.read("plugin.json"))
        assert manifest["extensions"]["com.openai"]["requires_local_executor"] is True
        server = json.loads(z.read("mcp.json"))["mcpServers"]["scenari"]
        assert server["type"] == "stdio"
        assert server["args"] == ["${PLUGIN_ROOT}/scripts/run_plugin.py"]
    # Rebuilding is deterministic, so releases are easy to compare and audit.
    second = build(ROOT, tmp_path / "plugin-again.zip")
    assert archive.read_bytes() == second.read_bytes()


def test_plugin_launcher_reports_setup_instead_of_downloading(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "run_plugin.py"
    script.write_text((ROOT / "scripts/run_plugin.py").read_text())
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 2
    assert not result.stdout
    assert "uv sync --locked --no-dev" in result.stderr


def test_plugin_launcher_uses_explicit_config_from_another_directory(tmp_path):
    config = tmp_path / "author.env"
    config.write_text("SCENARI_URL=https://example.test\nSCENARI_USERNAME=u\nSCENARI_PASSWORD=p\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_plugin.py"), "--version"],
        cwd=tmp_path,
        env={**os.environ, "SCENARI_ENV_FILE": str(config)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == json.loads((ROOT / "plugin.json").read_text())["version"]
