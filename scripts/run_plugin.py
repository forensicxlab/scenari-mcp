"""Launch the prepared plugin environment without downloads or stdout banners.

This bootstrap uses only the standard library and also runs on the system Python
3.9 supplied by macOS. The application itself runs in the prepared Python 3.12+ venv.
"""

import os
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print(
            "Scenari plugin setup is required. In the plugin directory run "
            "'uv sync --locked --no-dev' with Python 3.12+ available, "
            "then configure Scenari credentials and reconnect the plugin.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    args = [str(python), "-m", "scenari_mcp"]
    env_file = os.environ.get("SCENARI_ENV_FILE")
    if env_file:
        config = Path(env_file).expanduser()
        if not config.is_absolute():
            print("SCENARI_ENV_FILE must be an absolute path.", file=sys.stderr)
            raise SystemExit(2)
        args += ["--env-file", str(config)]
    elif (root / ".env").is_file():
        args += ["--env-file", str(root / ".env")]
    args += sys.argv[1:]
    os.execv(str(python), args)


if __name__ == "__main__":
    main()
