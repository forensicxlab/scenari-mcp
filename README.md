# Scenari MCP

A local stdio MCP and packaged skill for teachers creating digital-forensics
courses in **Dokiel**. Version 0.3 combines Scenari discovery and checked native writes with
teacher-led course-design guidance, revised Bloom alignment, practical work on
teacher-provided evidence, and native Dokiel content selection.

## Quick start with a local Scenari container

Follow [the container tutorial](docs/container-quickstart.md) to start the official
SCENARIsuite-starter image, install Dokiel, and connect this MCP. Already have
Scenari? Start below. Tested API/model combination: Scenari 6.5.4 and Dokiel
26.0.3 (en-US), with Training and Reference documentation extensions.

## Run locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Dependencies are pinned
in `uv.lock`.

```sh
git clone https://github.com/forensicxlab/scenari-mcp.git
cd scenari-mcp
uv sync --locked
cp .env.example .env
chmod 600 .env
# Edit .env with your Scenari credentials.
.venv/bin/scenari-mcp --env-file .env --check
```

Start the MCP server with:

```sh
.venv/bin/scenari-mcp --env-file /absolute/path/to/ScenariMCP/.env
```

The process waits for MCP messages on stdin. A startup banner is intentionally
absent: stdout is reserved for the protocol. `--check` is a separate diagnostic
mode that prints JSON and exits.

Environment variables take precedence over values in `--env-file`. No dotenv file
is loaded implicitly, so the server behaves consistently when launched from a
desktop client with a different working directory.

## Connect a client

For clients using the `mcpServers` JSON format, merge the entry in
[`examples/mcp-client.json`](examples/mcp-client.json) into their MCP configuration.
Replace its placeholder paths with absolute paths to your own checkout and dotenv file. For clients with a graphical MCP setup, use:

| Setting | Value |
| --- | --- |
| Transport | stdio |
| Command | `/absolute/path/to/scenari-mcp/.venv/bin/scenari-mcp` |
| Arguments | Two separate arguments: `--env-file` and `/absolute/path/to/scenari-mcp/.env` |

Suggested first request:

> Check the Scenari connection, list the Dokiel workspaces, then show me the
> available procedure and exercise item types in my chosen workspace. Read one
> existing procedure so we can inspect its structure.

## Install the MCP and skill together

The project is also a portable source plugin: [`plugin.json`](plugin.json) identifies
it, [`mcp.json`](mcp.json) declares the stdio server, and
[`skills/scenari-forensics-course-design`](skills/scenari-forensics-course-design/SKILL.md)
contains the skill and its references. Its policy allows automatic skill selection
for relevant course-design tasks in supporting clients. A model can also invoke
`$scenari-forensics-course-design` explicitly after installation. Selection remains
client-dependent; installing the package does not prove that a model followed it.

Build the distributable source ZIP:

```sh
.venv/bin/python scripts/build_plugin.py
```

The result is `dist/scenari-course-authoring-0.3.0.zip`. It contains the application
source, skill, manifests, dependency lock and launch script. It excludes `.env`,
virtual environments, caches, course evidence and generated course outputs.
Python 3.12+ and uv are prerequisites for preparing a new copy; this ZIP is not a
self-contained Python runtime or an offline dependency bundle.

For a supporting desktop/plugin host, install the extracted plugin using its
local-plugin mechanism. If the host copies plugins into a cache, prepare that
**installed copy**, rather than only the original source directory:

```sh
cd /absolute/path/to/installed/plugin
uv sync --locked --no-dev
```

Then configure the Scenari environment variables in the host, or set
`SCENARI_ENV_FILE` to the absolute path of a private dotenv file outside the plugin.
The launcher also accepts `.env` in the plugin root when no external env file is
selected. Keep credentials outside distributable archives.

The host expands `${PLUGIN_ROOT}` in `mcp.json`. The system `python3` starts the
standard-library launcher, which uses the prepared plugin `.venv` for the actual
application. The launcher performs no downloads or setup at MCP startup, and
reports a setup instruction on stderr if the environment is missing. Restart or
reconnect the server after preparation. No user-level plugin configuration is
changed by building this package.

For clients that support plain MCP but not packaged skills, the existing MCP
configuration still works. The server now sends the core teaching rules during
initialization and exposes the complete skill through resources and a guidance
tool. Hosts decide whether and how they present server instructions and resources
to the model. These are guidance; write checks are implemented in the server separately.

Packaging follows the [official portable plugin format](https://developers.openai.com/plugins/build/plugins)
and [local stdio launch format](https://developers.openai.com/plugins/deploy/desktop-only).
This repository prepares a local source bundle; it does not publish a plugin to a directory.

## Course-design guidance

The initialization instructions cover teacher co-design before drafting major
activities, goals and assessment aligned through Bloom, practical tasks grounded
in teacher-identified traces and evidence, and correct semantic Dokiel structures.
They also distinguish Kasm side-panel labs in e-learning from dedicated VMs used
alongside onsite slides. `VirtualMachineBlock.type` is an optional custom integration, requiring a compatible
block definition and web skin in the target workspace. It is not installed by the
MCP or the container quick start. See the delivery guidance before using it.

Four read-only Markdown resources expose the complete guidance:

| URI | Content |
| --- | --- |
| `scenari://authoring/overview` | Core skill and teacher co-design workflow |
| `scenari://authoring/practice` | Evidence-grounded practice, Bloom and assessment |
| `scenari://authoring/content` | Item models, definitions, citations and intention blocks |
| `scenari://authoring/delivery` | E-learning/Kasm and onsite conventions |

For hosts that expose only tools, call `get_authoring_guidance` with `section`
set to `overview`, `practice`, `content`, `delivery` or `all`. It serves the same
documents without Scenari API calls. Relative skill links are converted to the
corresponding MCP resource URIs. Python wheels include the skill, so guidance also
works when the server is installed outside this source tree.

## Tools

| Tool | Purpose |
| --- | --- |
| `get_authoring_guidance` | Retrieve the packaged teaching skill and references locally; defaults to the overview. |
| `check_connection` | Verify API authentication; report actual server version, API frame and Dokiel workspaces. |
| `list_workspaces` | Return workspace codes, model versions and extensions; defaults to Dokiel only. |
| `list_item_types` | Discover installed model IDs/signatures, with editorial descriptions for known Dokiel types. |
| `list_items` | Browse a folder's immediate children, including resources and subfolders. |
| `search_items` | Search literal title/code substrings or full text, optionally by model and folder subtree. |
| `read_item` | Retrieve XML, references, SHA-256, native model and current validation status. |
| `preview_item` | Build XML and check installed model, basic structure and existing links; never writes. |
| `create_item` | Create a new item, with optional intentional parent-folder creation and read-back verification. |
| `update_item` | Replace an item's complete content, requiring its current digest and retaining its native model. |

Use **exact workspace codes** from `list_workspaces`; titles are not implicitly
resolved. Content tools currently accept Dokiel workspaces only. Model IDs come
from `list_item_types`, such as `dk_concept`, `dk_stepList`, `dk_exercise`,
`dk_quizList` and `dk_module`. A guided exercise and an interactive quiz are distinct
Dokiel structures. The catalogue describes editorial intent, not the complete XML grammar.

Search example:

```json
{
  "workspace": "REPLACE_WITH_WORKSPACE_CODE",
  "model": "dk_stepList",
  "path": "/x_Playground",
  "limit": 10
}
```

`mode` defaults to `title`; use `full_text` for body content. Queries are literal
text, not raw regular expressions or XML. An empty query searches all items in
scope. Results use `next_offset` for pagination, with a maximum page size of 100.
Search ordering is supplied by Scenari; it is not a snapshot if content changes
between requests. Folder browsing paginates a bounded response fetched for that
folder, rather than recursively downloading a workspace.

`read_item` accepts absolute workspace paths or `id:` references returned in XML.
It does not download binary resources. The digest is calculated over the returned
UTF-8 XML; pass it to `update_item` as `expected_sha256`.

## Author native content

Writes are disabled by default. Set `SCENARI_ENABLE_WRITES=true` in the server's
environment or explicit dotenv file, then reconnect the MCP. `check_connection`
reports `writes_enabled`. The three authoring tools are discoverable in either
mode, and preview works while writes are disabled. Distributed examples default to false.

Use the same discriminated `item` object for preview, creation and replacement:

| `item.kind` | Native model | Creation extension |
| --- | --- | --- |
| `definition` | `dk_definition` | `.ref` |
| `bibliography` | `dk_bib` | `.ref` |
| `web_reference` | `dk_url` | `.url` |
| `concept` | `dk_concept` | `.unit` |
| `procedure` | `dk_stepList` | `.unit` |
| `theory` | `dk_theory` | `.unit` |
| `guided_exercise` | `dk_exercise` | `.unit` |
| `single_choice_quiz` | `dk_mcqSur` | `.quiz` |
| `assessment` | `dk_eval` | `.scen` |
| `module` | `dk_module` | `.scen` |
| `tutorial` | `dk_tutorial` | `.scen` |
| `publication` | `dk_tutorialRoot` | `.pub` |
| `xml` | Explicit installed `dk_*` model | Use the native extension for that model |

Structured text blocks support `information`, `tip`, `remark` and `warning` with
an optional title and a list of plain-text paragraphs. Procedures have real steps,
prerequisites and results; guided exercises have questions, solutions and hint
text; quizzes have choices, explanations, right/wrong feedback and a **one-based**
`correct_choice`. Structured hints are placed in the solution content; this does
not implement progressive release or teacher-only visibility. Preview reports a
recommended extension for supported models. MCP input schemas describe each kind's fields.

For example, call `preview_item` with:

```json
{
  "workspace": "REPLACE_WITH_WORKSPACE_CODE",
  "item": {
    "kind": "procedure",
    "title": "Record the acquisition context",
    "steps": [{
      "instruction": "Record the teacher-provided evidence identifier.",
      "details": [{"paragraphs": ["Use the identifier supplied with the lab materials."]}],
      "result": [{"paragraphs": ["The worksheet identifies the source being examined."]}]
    }]
  }
}
```

To create it, pass the same object to `create_item` with a new absolute `path`
ending in `.unit`. The parent must exist unless `create_parents=true` explicitly
allows missing folders. Creation checks that the target is absent. Dependencies
must exist and validate before a new item can link to them; known native slots
also check the linked item's model. Create references and quizzes before their
consumers, then assemble modules, tutorials and a publication item. Creating a
publication item saves source only; it does not generate or publish an output.

For additional native structures, use:

```json
{"kind": "xml", "model": "dk_stepList", "xml": "<sc:item ...>...</sc:item>"}
```

Supply complete, well-formed native XML with namespaces and one Dokiel root
matching the model. This path shares the installed-model, size, safe-XML,
reference, destination and read-back checks. It is not an arbitrary HTTP API.
Use inspected valid examples for inline citations, other quiz types, additional
semantic blocks or custom typed blocks. The four structured block types are a
deliberate initial subset; do not flatten other meanings into them. Binary upload,
deletion, output generation, publication, workspace administration and lab control
are outside the MCP tool surface. The Kasm block can be authored through verified
native XML; its side-panel rendering is provided by the separate version-2 web skin.

`update_item` replaces the **whole item**; it does not merge fields. Read first,
preserve content that should remain, and supply `expected_sha256`. A stale digest
is rejected and changing the native model is prohibited. The receipt includes
`previous_item` with the previous XML and digest for recovery; retain that receipt.

**Validation and concurrency limits:** preview checks basic structure and links,
not the complete Dokiel grammar. The saved item is checked for native model,
semantic XML equality (accounting for reference IDs/serialization) and Scenari's
`itSt` status. Only matching content with native status 1 yields `verified=true`.
Warning, invalid, pending and unknown statuses stay explicit. Inspect the receipt
before proceeding to dependent writes; recheck pending status with `read_item`.
Advanced XML can be saved even when Scenari marks it invalid. No automatic rollback
is attempted, because another editor may have changed it in the meantime.

Existence and digest checks run **before** PUT and serialize writes within one MCP
process. They are not an atomic server-side compare-and-swap and cannot lock other
Scenari editors or other MCP processes. Coordinate simultaneous editing. A timeout
or failed PUT response returns `write_applied="unknown"`; read the target before
retrying. An accepted PUT with failed read-back returns `write_applied=true` and
`verified=false`. No write is automatically retried.

## Configuration and limits

See [`.env.example`](.env.example). `SCENARI_URL` is the application root, before
`/~~chain` or `/~~static`. The default `SCENARI_EXEC_FRAME=script` is verified on
the dedicated instance. `web` can be selected for a differently configured server;
there is no automatic fallback. HTTPS verification remains enabled. HTTP is
accepted only on loopback for local development.

Every live Scenari operation passes through an API allowlist: discovery GETs and,
when explicitly enabled, only `wspSrc/PutSrc` for content creation/replacement.
Other operations and redirects are rejected. Credentials stay in the local environment or
ignored `.env`, and server error bodies are not returned to the MCP host. The
default per-request timeout is 20 seconds; the XML-input and response limit is 2 MiB,
including decompressed responses. Narrow requests or change `SCENARI_MAX_ITEM_BYTES` if needed.

The adapter uses `scsuitestarter-6-5` and `scenaripy-api`. Compatibility is verified
against the actual 6.5.4 instance; other server/model versions are not yet tested.
Version reporting does not imply that every server version is supported.

## Optional integrations

Custom web themes,Virtual lab access, VM images, proprietary training evidence and
Scenari/Dokiel model packs are not included in this release. Obtain compatible
models from Scenari. A standard Dokiel workspace works without the optional lab
panel. Content authors remain responsible for the evidence and lab access they
supply.

## Verify

Offline tests use a loopback-only fake API and include a real stdio MCP subprocess:

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
```

The test environment must permit binding a loopback socket. The tests never load
`.env` or contact the live instance. To verify the discovery tools, initialization
instructions and four resources, including live discovery against existing
content, run:

```sh
.venv/bin/python scripts/smoke_test.py --env-file .env
```

If several Dokiel workspaces are accessible, specify `--workspace <exact-code>`.
The smoke test requires an existing procedure or module to exercise item reading.

For an explicitly enabled end-to-end write test through stdio:

```sh
.venv/bin/python scripts/write_smoke_test.py --env-file .env --apply --receipt dist/write-smoke-receipt.json
```

It creates a unique `MCP_Write_Test_*` folder beneath `/x_Playground`, saves twelve
linked native item kinds and one advanced XML item, then updates its own procedure.
It verifies native validation/read-back and checks collision/stale-update rejection.
It does not update pre-existing course items or generate outputs. Test folders are
retained for inspection; the script provides no cleanup/deletion operation.

## Further iterations

Extend structured rich text, semantic blocks and quiz varieties, verify an authorized
Kasm session in the target delivery environment, and add MCP output previews
with checks for delivery mode and solution visibility.

References: [Scenari Python API](https://doc.scenari.software/SCENARIbuilder/apipython/fr/),
[Dokiel 26 reference](https://doc.scenari.software/Dokiel@26/reference/en/),
[official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Open-source release

Licensed under [MIT](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md),
[contributing](CONTRIBUTING.md), and [security reporting](SECURITY.md).
