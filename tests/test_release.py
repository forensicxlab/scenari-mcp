"""Public artifacts and private local bootstrap configuration contracts."""

import os
import re
import runpy
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("bash"), reason="The adapter runs in a Linux container")
@pytest.mark.parametrize("mode", ["zxf", "-xzf"])
def test_tar_adapter_preserves_paths_and_translates_upstream_arguments(tmp_path, mode):
    recorder = tmp_path / "record.sh"
    recorder.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
    recorder.chmod(0o700)
    adapter = tmp_path / "adapter.sh"
    adapter.write_text(
        (ROOT / "deploy/scenari/tar-compat.sh")
        .read_text()
        .replace("exec /usr/bin/bsdtar", 'exec "${TAR_COMPAT_TEST_EXECUTABLE}"')
    )
    result = subprocess.run(
        [
            "bash",
            str(adapter),
            mode,
            "a pack.tgz",
            "-C",
            "some folder",
            "--wildcards",
            "*/src",
            "--strip",
            "2",
        ],
        env={**os.environ, "TAR_COMPAT_TEST_EXECUTABLE": str(recorder)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == [
        "--strip-components",
        "2",
        "-" + mode.lstrip("-"),
        "a pack.tgz",
        "-C",
        "some folder",
        "*/src",
    ]


def test_local_initializer_pairs_credentials_and_preserves_existing_env(tmp_path):
    initialize = runpy.run_path(str(ROOT / "scripts/init_local.py"))["initialize"]
    existing = tmp_path / ".env"
    existing.write_text("private-existing-config\n")
    container, client = initialize(tmp_path)
    server = dotenv_values(container)
    mcp = dotenv_values(client)
    assert mcp["SCENARI_PASSWORD"] == server["SC_SUPERADMIN_PASSWORD"]
    assert server["SC_SYSTEM_PASSWORD"] != mcp["SCENARI_PASSWORD"]
    assert len(mcp["SCENARI_PASSWORD"]) == 64
    assert mcp["SCENARI_ENABLE_WRITES"] == "false"
    assert mcp["SCENARI_URL"] == "http://127.0.0.1:18080/scenari"
    assert existing.read_text() == "private-existing-config\n"
    if os.name != "nt":
        assert container.stat().st_mode & 0o777 == 0o600
        assert client.stat().st_mode & 0o777 == 0o600
    before = {p: p.read_bytes() for p in [container, client]}
    with pytest.raises(SystemExit, match="will not replace"):
        initialize(tmp_path)
    assert all(p.read_bytes() == contents for p, contents in before.items())


def test_public_release_is_self_contained_and_excludes_private_assets(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    build = runpy.run_path(str(ROOT / "scripts/build_public_release.py"))["build_release"]
    path = build(ROOT, tmp_path / "source.zip")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert {
            "LICENSE",
            "docs/container-quickstart.md",
            "deploy/scenari/compose.yaml",
            ".github/workflows/ci.yml",
            "tests/test_release.py",
            "scripts/build_plugin.py",
            "scripts/init_local.py",
        } <= names
        assert not any(
            name.startswith(("themes/", "docs/theme-redesign/", "dist/", ".venv/"))
            or "receipt" in name
            or Path(name).name in {".env", ".env.local"}
            for name in names
        )
        for name in names:
            assert not re.search(rb"/Users/[\w.-]+/(?:work|Desktop)/", archive.read(name))
        archive.extractall(tmp_path / "clean")
    # Public packaging must work again from only the exported source files.
    clean = tmp_path / "clean"
    assert build(clean, tmp_path / "rebuilt.zip").read_bytes() == path.read_bytes()
