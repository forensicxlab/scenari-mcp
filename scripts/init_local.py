"""Generate private local-container/MCP configuration without replacing existing files."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def initialize(root: Path = ROOT) -> tuple[Path, Path]:
    container = root / "deploy/scenari/.env"
    client = root / ".env.local"
    if container.exists() or client.exists():
        raise SystemExit(
            "Local configuration already exists. Keep the current files; "
            "this initializer will not replace credentials."
        )
    password = secrets.token_hex(32)
    contents = {
        container: (
            f"SC_SUPERADMIN_PASSWORD={password}\nSC_SYSTEM_PASSWORD={secrets.token_hex(32)}\n"
        ),
        client: (
            "SCENARI_URL=http://127.0.0.1:18080/scenari\n"
            "SCENARI_USERNAME=superadmin\n"
            f"SCENARI_PASSWORD={password}\n"
            "SCENARI_EXEC_FRAME=script\n"
            "SCENARI_ENABLE_WRITES=false\n"
        ),
    }
    for path, content in contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
    return container, client


if __name__ == "__main__":
    for config in initialize():
        print(f"Created private configuration: {config}")
    print("Existing .env is untouched. Use --env-file .env.local for the local container.")
