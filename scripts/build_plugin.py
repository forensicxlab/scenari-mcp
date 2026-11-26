"""Build a source plugin ZIP from an explicit allowlist; never bundle local credentials."""

import argparse
import json
import re
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_files(root: Path) -> list[Path]:
    selected = [
        root / name
        for name in (
            "plugin.json",
            "mcp.json",
            "pyproject.toml",
            "uv.lock",
            "README.md",
            ".env.example",
            ".python-version",
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "docs/container-quickstart.md",
            "docs/releasing.md",
            "deploy/scenari/compose.yaml",
            "deploy/scenari/compose.tar-compat.yaml",
            "deploy/scenari/Dockerfile.tar-compat",
            "deploy/scenari/tar-compat.sh",
            "deploy/scenari/.dockerignore",
            "scripts/init_local.py",
            "scripts/run_plugin.py",
            "scripts/smoke_test.py",
            "scripts/write_smoke_test.py",
        )
    ]
    selected += list((root / "src/scenari_mcp").rglob("*.py"))
    for pattern in ("*.md", "*.yaml"):
        selected += list((root / "skills").rglob(pattern))
    for path in selected:
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError(
                f"Package input must be a regular file inside the project: {path.name}"
            )
    return sorted(set(selected))


def build_plugin(root: Path, output: Path | None = None) -> Path:
    manifest = json.loads((root / "plugin.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    if manifest["version"] != project["project"]["version"]:
        raise ValueError("Plugin and Python package versions must agree.")
    files = package_files(root)
    relative_paths = {p.relative_to(root).as_posix() for p in files}
    for path in files:
        if path.suffix == ".md" and "skills" in path.relative_to(root).parts:
            for destination in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" not in destination:
                    target = (path.parent / destination).resolve()
                    if not target.is_relative_to(root.resolve()):
                        raise ValueError("A skill reference escapes the package.")
                    if target.relative_to(root.resolve()).as_posix() not in relative_paths:
                        raise ValueError(
                            f"A skill reference is missing from the package: {destination}"
                        )
    if output is None:
        output = root / "dist" / f"{manifest['name']}-{manifest['version']}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build_plugin(ROOT, args.output))


if __name__ == "__main__":
    main()
