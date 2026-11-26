# From an empty machine to a Dokiel MCP

This walkthrough runs the official **SCENARIsuite-starter** container and the MCP
as a local Python stdio process. The image name is `scenari/suite-starter`, not
`scenaristarter-suite`. Docker is only needed for Scenari; the MCP client launches
the Python server directly.

## 1. Prerequisites

Install [Docker with Compose v2](https://docs.docker.com/compose/install/),
[Python 3.12+ and uv](https://docs.astral.sh/uv/getting-started/installation/).
Clone the public repository and enter its directory:

```sh
git clone https://github.com/forensicxlab/scenari-mcp.git
cd scenari-mcp
```

The example pins Scenari 6.5.4 and its image digest. The registry manifest supplies
`linux/amd64`; ARM machines need Docker's amd64 emulation. Allow several GB of
free disk and sufficient Docker memory for a 1 GiB Java heap plus image tools.
The first image download is large and startup can take several minutes.
If amd64 emulation produces `tar: ... Function not implemented`, use the tested
compatibility variant described under Troubleshooting below.

## 2. Generate local configuration

```sh
uv sync --locked
uv run python scripts/init_local.py
```

The initializer creates two private files with generated random credentials:

- `deploy/scenari/.env`: container administrator and system-account passwords.
- `.env.local`: MCP connection settings for this new local server; writes disabled.

It refuses to overwrite either file and preserves an existing root `.env`.
Keep both generated files for subsequent starts. They are ignored by Git.
For the browser login, read `SC_SUPERADMIN_PASSWORD` locally from the container
file; do not paste it into chat, issues or screenshots. The account is `superadmin`.

## 3. Start Scenari

From the repository root:

```sh
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml up -d
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml ps
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml logs --tail 60 scenari
```

Open <http://127.0.0.1:18080/scenari/&> and sign in. The image's native health check
must become healthy. The service binds only to localhost. Scenari's data lives in
the named `scenari-data` volume. `SC_WEBAPP_NAME`, `SC_PUBLIC_URL`, language,
password variables and the data location follow the
[publisher's image documentation](https://hub.docker.com/r/scenari/suite-starter).
The [upstream entrypoint](https://source.scenari.software/projects/suite-starter/repository/git/revisions/6.5/entry/docker/SCENARIsuite-starter/docker-entrypoint.sh)
configures the supplied passwords on startup. This guide uses explicit passwords
rather than relying on any default interactive account.

## 4. Install Dokiel and create a workspace

The image is an application server; do not assume it contains the required
document models. Obtain the **Dokiel 26 en-US `.wsppack`**, its matching Training
and Reference documentation extensions from the
[official Dokiel download page](https://download.scenari.software/Dokiel/).
Use a release compatible with Scenari 6.5. The MCP was tested with **26.0.3**;
different versions need verification.

In Scenari's administration interface, open pack management, install the Dokiel
pack and the two matching extension packs, then create a Dokiel workspace named
`My first course`. Enable the Training and Reference documentation extensions in
its properties. Labels vary with the server language. Models are installed
separately from Scenari; see [the official model overview](https://doc.scenari.software/Dokiel/en/).

These are administrator steps: this MCP does not install packs, manage users or
create workspaces. For ongoing use, create a dedicated authoring account with
access to this workspace and replace the bootstrap superadmin credentials in
`.env.local` with that account's credentials.

## 5. Check the MCP connection

```sh
uv run scenari-mcp --env-file .env.local --check
```

Expect `connected: true`, the actual server version and your Dokiel workspace.
An empty workspace list usually means packs/workspace creation or account access
still needs attention. The configuration URL is the application root
`http://127.0.0.1:18080/scenari`, without `/~~chain` or a home-page suffix.

## 6. Connect your MCP client

Merge this entry into the client's MCP configuration, replacing **both** absolute
paths with paths on your machine:

```json
{
  "mcpServers": {
    "scenari": {
      "command": "/absolute/path/to/scenari-mcp/.venv/bin/scenari-mcp",
      "args": ["--env-file", "/absolute/path/to/scenari-mcp/.env.local"]
    }
  }
}
```

On Windows, use `.venv/Scripts/scenari-mcp.exe`. In a graphical setup, enter
`--env-file` and the path as **two separate arguments**. A joined argument such
as `--env-file/path/to/.env.local` causes startup to exit before the handshake.
Do not add `--check` to the persistent MCP launch command; it exits after diagnostics.
Environment variables supplied by the host override values from the dotenv file.

Reconnect the client and ask:

> Check the connection and list my Dokiel workspaces. Retrieve the authoring
> guidance, then help me agree learning goals and a small practical exercise
> before drafting content. Use the workspace code returned by discovery.

The MCP provides teacher-led design guidance as initialization instructions,
resources and `get_authoring_guidance`. Client handling of those mechanisms varies.

## 7. Try a first write

Preview a small procedure first. After reviewing it, set
`SCENARI_ENABLE_WRITES=true` in `.env.local` and reconnect the client. Ask it to
create the agreed procedure at `/Getting_Started/first_procedure.unit`, explicitly
allowing parent-folder creation. Check the returned native validation status and
open the item in Scenari. The API can create content sources; generation and
publication are performed in Scenari's UI.

For a disposable test workspace with writes enabled, the optional integration
test creates a new test folder and retains it for inspection:

```sh
uv run python scripts/write_smoke_test.py --env-file .env.local --workspace YOUR_WORKSPACE_CODE --apply --receipt dist/local-write-receipt.json
```

For a read-only test against a workspace that already contains a module/procedure:

```sh
uv run python scripts/smoke_test.py --env-file .env.local --workspace YOUR_WORKSPACE_CODE
```

## Stop, restart and keep data

```sh
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml down
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml up -d
```

The named volume survives `down`. Adding `--volumes` deletes the stored server
data; use that only for an intentional reset. Before upgrades, use the
[publisher's backup/restore procedure](https://hub.docker.com/r/scenari/suite-starter#backup--restore--checkdb)
and test recovery. Changing the image tag does not establish model compatibility.

## Troubleshooting

### GNU tar failure under amd64 emulation

Some emulators cannot run GNU tar's `openat2` extraction path; see the
[upstream emulator issue](https://github.com/orbstack/orbstack/issues/2588).
This occurred on the Apple Silicon test host. The image then continued starting
Jetty without the Scenari web application. Our additional HTTP health check detects
that condition. Use this optional variant, retaining the same data volume and credentials:

```sh
docker compose --project-directory deploy/scenari -f deploy/scenari/compose.yaml -f deploy/scenari/compose.tar-compat.yaml up -d --build
```

It builds from the same pinned official image, installs `libarchive-tools` and
uses BSD tar through a small argument adapter. It preserves the upstream
entrypoint and runs Scenari as its original `jetty` user. No privileged mode or
relaxed container security profile is required. Continue using both `-f` options
for subsequent lifecycle commands for this variant. Native amd64 hosts can use
the unmodified upstream image when it works on their kernel/runtime.

### Other symptoms

| Symptom | Check |
| --- | --- |
| Port 18080 occupied | Stop the conflicting service or change the Compose host port, `SC_PUBLIC_URL` and `.env.local` URL together. |
| Container unhealthy | Inspect `ps` and logs; allow startup time, check disk/memory and ARM emulation. |
| `401` | Check the account/password and any host environment overriding `.env.local`. |
| `403` | Check the account's workspace permissions and script API access. |
| `404` or redirect | Use the exact app root configured above; the MCP does not follow redirects. |
| Startup connection closes | Check executable and separate arguments; run `--check` outside the client. |
| No banner when launched manually | Normal: stdio startup waits for protocol messages. |
| Downloaded e-learning looks different | Preview it over local HTTP rather than `file://`; some features require same-origin frame/script access. |

This setup is for a single-computer evaluation. For shared deployment, configure
HTTPS and the public URL, use restricted accounts, manage secrets and arrange
backups. The MCP never disables TLS verification; HTTP is accepted only on loopback.

## Verification scope

On 26 November 2026, the pinned image plus the tar-compat override was started on
an Apple Silicon host. The native administrative health check and MCP connection
diagnostic passed against Scenari 6.5.4 with generated credentials. The stock
image hit the documented tar/emulation failure on that host. Dokiel installation
and workspace creation in step 4 are manual prerequisites, not automated by this
Compose example. The MCP's Dokiel authoring workflow was separately verified on
Scenari 6.5.4 / Dokiel 26.0.3; offline tests do not replace testing your model packs.
