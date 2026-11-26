"""Explicit environment configuration; credentials never appear in repr or tool results."""

import math
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """An actionable configuration error safe to display to an MCP client."""


@dataclass(frozen=True)
class Settings:
    url: str
    username: str
    password: str = field(repr=False)
    exec_frame: str = "script"
    timeout_seconds: float = 20
    max_item_bytes: int = 2 * 1024 * 1024
    enable_writes: bool = False

    def __post_init__(self) -> None:
        parts = urlsplit(self.url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
        ):
            raise ConfigurationError(
                "SCENARI_URL must be an application root URL "
                "without credentials, query or fragment."
            )
        if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ConfigurationError(
                "Use HTTPS for SCENARI_URL; HTTP is supported only on loopback."
            )
        if "/~~" in parts.path or parts.path.endswith((".xhtml", ".html")):
            raise ConfigurationError(
                "SCENARI_URL must point to the application root, before /~~chain or /~~static."
            )
        if not self.username.strip() or not self.password:
            raise ConfigurationError("Set SCENARI_USERNAME and SCENARI_PASSWORD.")
        if self.exec_frame not in {"script", "web"}:
            raise ConfigurationError("SCENARI_EXEC_FRAME must be script or web.")
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 120:
            raise ConfigurationError(
                "SCENARI_TIMEOUT_SECONDS must be greater than 0 and at most 120."
            )
        if not 1024 <= self.max_item_bytes <= 10 * 1024 * 1024:
            raise ConfigurationError("SCENARI_MAX_ITEM_BYTES must be between 1024 and 10485760.")

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [
            name
            for name in ("SCENARI_URL", "SCENARI_USERNAME", "SCENARI_PASSWORD")
            if not os.getenv(name)
        ]
        if missing:
            raise ConfigurationError("Missing configuration: " + ", ".join(missing))
        writes = os.getenv("SCENARI_ENABLE_WRITES", "false").lower()
        if writes not in {"true", "false"}:
            raise ConfigurationError("SCENARI_ENABLE_WRITES must be true or false.")
        try:
            return cls(
                url=os.environ["SCENARI_URL"].strip().rstrip("/"),
                username=os.environ["SCENARI_USERNAME"],
                password=os.environ["SCENARI_PASSWORD"],
                exec_frame=os.getenv("SCENARI_EXEC_FRAME", "script"),
                timeout_seconds=float(os.getenv("SCENARI_TIMEOUT_SECONDS", "20")),
                max_item_bytes=int(os.getenv("SCENARI_MAX_ITEM_BYTES", "2097152")),
                enable_writes=writes == "true",
            )
        except (ValueError, OverflowError) as exc:
            if isinstance(exc, ConfigurationError):
                raise
            raise ConfigurationError(
                "Timeout and item-size configuration must be valid numbers."
            ) from None
