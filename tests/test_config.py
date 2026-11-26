from dataclasses import replace

import pytest

from scenari_mcp.config import ConfigurationError, Settings


def test_missing_settings_and_secret_repr(monkeypatch):
    for name in ["SCENARI_URL", "SCENARI_USERNAME", "SCENARI_PASSWORD"]:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError, match="SCENARI_URL"):
        Settings.from_env()
    assert "private-password" not in repr(
        Settings("https://example.test", "user", "private-password")
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test",
        "https://user:secret@example.test",
        "https://example.test/~~chain",
        "https://example.test/home.xhtml",
        "https://example.test/?secret=x",
        "https://example.test/#fragment",
    ],
)
def test_rejects_bad_application_urls(url):
    with pytest.raises(ConfigurationError):
        Settings(url, "user", "secret")


@pytest.mark.parametrize("timeout", [0, -1, 121, float("nan"), float("inf")])
def test_timeout_must_be_finite_and_bounded(timeout):
    with pytest.raises(ConfigurationError):
        replace(Settings("https://example.test", "user", "secret"), timeout_seconds=timeout)


def test_write_configuration_is_explicit(monkeypatch):
    for name, value in {
        "SCENARI_URL": "https://example.test",
        "SCENARI_USERNAME": "u",
        "SCENARI_PASSWORD": "p",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("SCENARI_ENABLE_WRITES", raising=False)
    assert not Settings.from_env().enable_writes
    monkeypatch.setenv("SCENARI_ENABLE_WRITES", "true")
    assert Settings.from_env().enable_writes
    monkeypatch.setenv("SCENARI_ENABLE_WRITES", "maybe")
    with pytest.raises(ConfigurationError, match="SCENARI_ENABLE_WRITES"):
        Settings.from_env()
