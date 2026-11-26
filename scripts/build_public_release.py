"""Build a clean repository ZIP, excluding private development pilots and assets."""

import json
import zipfile
from pathlib import Path

from build_plugin import package_files

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TESTS = (
    "conftest.py",
    "test_client.py",
    "test_config.py",
    "test_writing.py",
    "test_stdio.py",
    "test_packaging.py",
    "test_release.py",
)


def build_release(root: Path = ROOT, output: Path | None = None) -> Path:
    files = package_files(root) + [
        root / path
        for path in [
            ".gitignore",
            ".github/workflows/ci.yml",
            "scripts/build_plugin.py",
            "scripts/build_public_release.py",
            "examples/mcp-client.json",
            *["tests/" + name for name in PUBLIC_TESTS],
        ]
    ]
    for path in files:
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError("Release input must be a regular file inside the project.")
    version = json.loads((root / "plugin.json").read_text())["version"]
    output = output or root / "dist" / f"scenari-mcp-{version}-source.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return output


if __name__ == "__main__":
    print(build_release())
