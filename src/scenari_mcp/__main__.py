"""Console entry point: stdout belongs exclusively to MCP unless --check is selected."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from . import __version__
from .client import ScenariClient, ScenariError
from .config import ConfigurationError, Settings
from .server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scenari/Dokiel discovery and authoring over stdio."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--env-file", type=Path, help="Explicit dotenv file; process environment takes precedence."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print a connection diagnostic as JSON, then exit (does not start MCP).",
    )
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.exit(2, "Configuration error: the specified env file does not exist.\n")
        load_dotenv(args.env_file, override=False)
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    if args.check:
        try:
            with ScenariClient(settings) as client:
                result = client.check_connection()
        except ScenariError as exc:
            parser.exit(1, f"{exc}\n")
        except Exception:
            parser.exit(
                1, "INVALID_RESPONSE: Scenari returned an unexpected connection response.\n"
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    create_server(settings).run(transport="stdio")


if __name__ == "__main__":
    main()
