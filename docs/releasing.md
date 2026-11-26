# Prepare a public release

The development directory can contain private local pilots. Publish the clean
source snapshot built below, not an unfiltered copy of the directory.

```sh
uv sync --locked
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run python scripts/build_public_release.py
uv run python scripts/build_plugin.py
uv build
```

`dist/scenari-mcp-0.3.0-source.zip` is the repository snapshot. It includes the MCP,
skill, offline tests, Compose quick start, documentation, MIT license and CI.
`dist/scenari-course-authoring-0.3.0.zip` is the smaller MCP/skill plugin.
Both builders use explicit allowlists. Generated configurations, installed
libraries, local assets, course exports, receipts and private pilots are excluded.

The repository is [forensicxlab/scenari-mcp](https://github.com/forensicxlab/scenari-mcp).
The MIT copyright holder is **ForensicXlab**, as recorded in `LICENSE`. Dependency
and Scenari asset licenses remain separate; see `THIRD_PARTY_NOTICES.md`.

Before a release, extract the source ZIP into a fresh directory, run
`uv sync --locked` and the offline tests there, and inspect the files. Review the
Git diff in this public checkout before committing. Keep private development
history and deployment data outside this repository.

For a prepared checkout with `origin` already configured:

```sh
git status --short
git diff
# Stage only the reviewed public files, then commit.
git add .
git diff --cached --stat
git commit -m "Prepare open-source MCP and container quick start"
# Push when you are ready to publish the commit.
git push origin main
```

Enable GitHub private vulnerability reporting if desired. `SECURITY.md` describes
private reporting without assuming the feature is already enabled. The build
scripts create local artifacts; they never commit, push or upload.

Release versions must agree in `pyproject.toml`, `plugin.json` and
`src/scenari_mcp/__init__.py`; refresh `uv.lock` after metadata changes. Attach
reviewed archives to a tag/release if desired. The CI workflow runs offline tests,
lint and packaging; it does not claim an unattended Dokiel container integration test.
