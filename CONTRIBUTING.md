# Contributing

Use Python 3.12+ and uv. From the checkout:

```sh
uv sync --locked
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
```

Offline tests use a loopback fake API and stdio MCP subprocesses. No live server
or credentials are required. Test against a disposable Dokiel workspace when
checking integration behavior. Never submit real evidence, credentials, access
URLs, workspace exports or personal paths in a PR or issue.

For changes to writes, cover invalid references, failed read-back, concurrency
and the distinction between an accepted PUT and verified valid content. Preserve
the write opt-in, transport allowlist and no-automatic-retry behavior. Do not
print application logs to stdout: it carries the stdio MCP protocol.

Keep version values in `pyproject.toml`, `plugin.json` and
`src/scenari_mcp/__init__.py` consistent. Run both release builders after changing
packaging. Changes to teacher guidance should preserve teacher co-design, Bloom
alignment, evidence-grounded practical work and semantic Dokiel item selection.

Contributions are submitted under the project's MIT license. Include validation
results and a short explanation of the resulting behavior with each PR.
