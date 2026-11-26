"""Discovery and explicit, checked Dokiel authoring over stdio."""

from collections.abc import Callable
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .authoring import ItemSpec
from .client import ScenariClient, ScenariError
from .config import Settings
from .guidance import SERVER_INSTRUCTIONS, Section, get_guidance, register_resources
from .writing import AuthoringClient

PageSize = Annotated[int, Field(ge=1, le=100)]
Offset = Annotated[int, Field(ge=0)]
Query = Annotated[str, Field(max_length=500)]
Workspace = Annotated[str, Field(min_length=1, max_length=128)]
Reference = Annotated[str, Field(min_length=1, max_length=2048)]


def create_server(
    settings: Settings,
    client_factory: Callable[[Settings], ScenariClient] = AuthoringClient,
) -> MCPServer:
    server = MCPServer(
        "scenari",
        version=__version__,
        instructions=SERVER_INSTRUCTIONS,
        log_level="WARNING",
    )
    annotations = ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
    register_resources(server)

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        )
    )
    def get_authoring_guidance(section: Section = "overview") -> dict[str, Any]:
        """Read course-design guidance before authoring: teacher co-design, Bloom, evidence,
        native Dokiel structures and delivery modes. Works locally without Scenari API calls.
        Select overview first, then practice, content or delivery as needed; all returns every
        section. Use this tool when the client does not expose the authoring resources.
        """
        return get_guidance(section)

    def invoke(method: str, **kwargs) -> dict:
        try:
            with client_factory(settings) as client:
                return getattr(client, method)(**kwargs)
        except ScenariError as exc:
            raise ToolError(str(exc)) from None
        except Exception:
            # SDK exceptions may include raw server responses. Never return those to the host.
            raise ToolError(
                "INVALID_RESPONSE: Scenari returned an unexpected response. "
                "Check the server version, workspace and selected item type."
            ) from None

    @server.tool(annotations=annotations)
    def check_connection() -> dict[str, Any]:
        """Check authentication, report the actual server version and discover Dokiel workspaces.

        Does not change server state.
        """
        return invoke("check_connection")

    @server.tool(annotations=annotations)
    def list_workspaces(dokiel_only: bool = True) -> dict[str, Any]:
        """List accessible workspaces with exact codes, model versions and extensions.

        Defaults to Dokiel only.
        """
        return invoke("list_workspaces", dokiel_only=dokiel_only)

    @server.tool(annotations=annotations)
    def list_item_types(workspace: Workspace, dokiel_only: bool = True) -> dict[str, Any]:
        """Discover installed item model IDs and signatures, with guidance for known Dokiel types.

        This is a type catalogue, not a creation schema.
        """
        return invoke("list_item_types", workspace=workspace, dokiel_only=dokiel_only)

    @server.tool(annotations=annotations)
    def list_items(
        workspace: Workspace, path: Reference = "/", limit: PageSize = 50, offset: Offset = 0
    ) -> dict[str, Any]:
        """Browse immediate children of a workspace folder. Start at / and follow returned paths.

        Includes folders and resource items; results are paginated.
        """
        return invoke("list_items", workspace=workspace, path=path, limit=limit, offset=offset)

    @server.tool(annotations=annotations)
    def search_items(
        workspace: Workspace,
        query: Query = "",
        mode: Literal["title", "full_text"] = "title",
        model: str | None = None,
        path: Reference = "/",
        limit: PageSize = 25,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        """Find reusable content by literal title/code substring or full text.

        Optionally filter by model ID and folder subtree. Empty query lists matching items.
        Use next_offset for another page.
        """
        return invoke(
            "search_items",
            workspace=workspace,
            query=query,
            mode=mode,
            model=model,
            path=path,
            limit=limit,
            offset=offset,
        )

    @server.tool(annotations=annotations)
    def read_item(workspace: Workspace, reference: Reference) -> dict[str, Any]:
        """Read a native XML item by absolute workspace path or id: reference.

        Returns intact XML, linked references, SHA-256 and native model/validation status.
        Binary resources and folders are not XML items.
        """
        return invoke("read_item", workspace=workspace, reference=reference)

    @server.tool(annotations=annotations)
    def preview_item(workspace: Workspace, item: ItemSpec) -> dict[str, Any]:
        """Preview native XML; check installed model and existing links without writing.

        Choose item.kind by meaning: procedure, guided_exercise, single_choice_quiz, definition,
        bibliography, web_reference, concept, theory, assessment, module, tutorial or publication.
        kind=xml accepts advanced native XML and a dk_* model ID. It checks basic structure,
        not the full model grammar. Scenari performs full validation only after saving.
        Read authoring guidance and agree substantial activities with the teacher first.
        """
        return invoke("preview_item", workspace=workspace, item=item)

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
        )
    )
    def create_item(
        workspace: Workspace, path: Reference, item: ItemSpec, create_parents: bool = False
    ) -> dict[str, Any]:
        """Create one native Dokiel item at a new absolute path. Requires writes enabled.

        Uses the same input as preview_item. Rejects existing files/folders and broken links.
        Set create_parents=true only to intentionally create missing enclosing folders.
        Create dependencies before items linking to them. Checks are not an atomic server lock.
        Inspect write_applied, verified, status and content_matches; saving alone is insufficient.
        If outcome is unknown, read the path before retrying. Does not generate or publish output.
        """
        return invoke(
            "create_item", workspace=workspace, path=path, item=item, create_parents=create_parents
        )

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True
        )
    )
    def update_item(
        workspace: Workspace,
        reference: Reference,
        expected_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")],
        item: ItemSpec,
    ) -> dict[str, Any]:
        """Replace an existing XML item's complete content while retaining its native model.

        Read the item first. Supply its returned sha256 to detect intervening edits at preflight.
        This is not an atomic server-side compare-and-swap; avoid simultaneous external edits.
        Preserve content you intend to keep, using kind=xml for unsupported structures. No merge
        occurs. Receipt includes previous_item for recovery. Inspect verification and validation
        status; failures never trigger an automatic retry or rollback. Requires writes enabled.
        """
        return invoke(
            "update_item",
            workspace=workspace,
            reference=reference,
            expected_sha256=expected_sha256,
            item=item,
        )

    return server
