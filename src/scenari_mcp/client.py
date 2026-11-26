"""Bounded transport around the official Scenari Python client."""

import hashlib
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlsplit

import requests
import scenaripy_api
from defusedxml import ElementTree as SafeET
from scsuitestarter_6_5.api.item import ESrcField
from scsuitestarter_6_5.api.search import Request, SearchFree
from scsuitestarter_6_5.portal import ScPortal

from .catalog import describe_type
from .config import Settings

SC_NS = "http://www.utc.fr/ics/scenari/v3/core"


class ScenariError(RuntimeError):
    """A stable error without response bodies, credentials or raw HTTP exceptions."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


class ReadOnlySession(requests.Session):
    """Discovery GETs; subclasses may explicitly enable the sole content PUT action."""

    content_writes = False

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.auth = (settings.username, settings.password)
        self._base = f"{settings.url.rstrip('/')}/~~chain/{settings.exec_frame}/u/"

    def send(self, request: requests.PreparedRequest, **kwargs) -> requests.Response:
        allowed = {
            "adminServer": {"GetServerInfo"},
            "adminWsp": {"List"},
            "itemType": {"List"},
            "wspSrc": {"GetSrc"},
            "search": {None},
        }
        target = urlsplit(request.url)
        base = urlsplit(self._base)
        service = target.path.removeprefix(base.path)
        actions = parse_qs(target.query).get("cdaction", [None])
        read = request.method == "GET" and service in allowed and actions[0] in allowed[service]
        write = (
            self.content_writes
            and self.settings.enable_writes
            and request.method == "PUT"
            and service == "wspSrc"
            and actions == ["PutSrc"]
        )
        if (
            not (read or write)
            or target.scheme != base.scheme
            or target.netloc != base.netloc
            or not target.path.startswith(base.path)
            or len(actions) != 1
        ):
            raise ScenariError(
                "READ_ONLY", "This session rejects requests outside its API allowlist."
            )
        kwargs["timeout"] = self.settings.timeout_seconds
        kwargs["allow_redirects"] = False
        kwargs["stream"] = True
        response = None
        try:
            response = super().send(request, **kwargs)
            status = response.status_code
            if status == 401:
                raise ScenariError(
                    "AUTHENTICATION_FAILED", "Check the configured Scenari username and password."
                )
            if status == 403:
                raise ScenariError(
                    "ACCESS_DENIED",
                    "The account cannot access this service or workspace. "
                    "Check permissions and SCENARI_EXEC_FRAME.",
                )
            if status == 404:
                raise ScenariError(
                    "NOT_FOUND", "The requested service, workspace or item was not found."
                )
            if status in {409, 412}:
                raise ScenariError("CONFLICT", "Scenari rejected a conflicting content change.")
            if 300 <= status < 400:
                raise ScenariError(
                    "REDIRECT",
                    "The API redirected the request. Check SCENARI_URL and the API frame; "
                    "redirects are not followed.",
                )
            if status != 200:
                raise ScenariError("HTTP_ERROR", f"Scenari returned HTTP {status}.")
            chunks = []
            size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > self.settings.max_item_bytes:
                    raise ScenariError(
                        "RESPONSE_TOO_LARGE",
                        "The response exceeds SCENARI_MAX_ITEM_BYTES. "
                        "Narrow the request or adjust the configured limit.",
                    )
                chunks.append(chunk)
            response._content = b"".join(chunks)
            return response
        except requests.exceptions.SSLError:
            raise ScenariError(
                "TLS_ERROR", "TLS verification failed. Check the certificate trust configuration."
            ) from None
        except requests.exceptions.Timeout:
            raise ScenariError(
                "TIMEOUT", "Scenari did not respond within SCENARI_TIMEOUT_SECONDS."
            ) from None
        except requests.exceptions.RequestException:
            raise ScenariError(
                "CONNECTION_FAILED",
                "Cannot reach Scenari. Check the configured URL, network and DNS.",
            ) from None
        finally:
            if response is not None:
                response.close()


def validate_reference(value: str, *, folder: bool = False) -> str:
    if not value or any(ord(c) < 32 for c in value):
        raise ScenariError(
            "INVALID_REFERENCE", "Provide an absolute workspace path or an id: reference."
        )
    if not folder and value.startswith("id:") and re.fullmatch(r"id:[A-Za-z0-9_-]+", value):
        return value
    if not value.startswith("/") or any(part in {".", ".."} for part in value.split("/")):
        raise ScenariError(
            "INVALID_REFERENCE", "Use an absolute workspace path without . or .. segments."
        )
    return "/" + "/".join(part for part in value.split("/") if part)


def build_search(query: str, mode: str, model: str | None, path: str) -> SearchFree:
    """Use the SDK's free criterion with safe XML attribute quoting.

    The SDK's convenience criteria use text escaping inside XML attributes,
    which does not escape double quotes. ElementTree handles both correctly.
    """
    root = ET.Element("and")
    prefix = path.rstrip("/") + "/"
    ET.SubElement(root, "exp", type="Items", afterUri=prefix, beforeEndFolder=prefix)
    if query:
        if mode == "title":
            # Escape only regex metacharacters; Python's re.escape adds Java-invalid escapes.
            escaped = re.sub(r"([\\.^$|?*+()\[\]{}])", r"\\\1", query)
            ET.SubElement(root, "exp", type="ItemCodeOrTitle", regexp="(?i)" + escaped)
        else:
            ET.SubElement(root, "exp", type="FullText", textSearch=query, options=";c;")
    if model:
        if not re.fullmatch(r"[A-Za-z0-9_]+", model):
            raise ScenariError("INVALID_MODEL", "Use a model ID returned by list_item_types.")
        ET.SubElement(root, "exp", type="ItemModel", models=model)
    return SearchFree(ET.tostring(root, encoding="unicode"))


def workspace_summary(wsp: dict) -> dict:
    return {
        "code": wsp["wspCd"],
        "title": wsp.get("title", ""),
        "status": wsp.get("status"),
        "model": wsp.get("wspType", {}),
        "extensions": wsp.get("wspOptions", []),
        "description": wsp.get("props", {}).get("desc", ""),
    }


class ScenariClient:
    """One short-lived SDK session per MCP call; no shared mutable session state."""

    session_type = ReadOnlySession

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = self.session_type(settings)
        self.portal = ScPortal(settings.username, settings.password)
        self.portal.add_chain_portlet(
            f"{settings.url.rstrip('/')}/~~chain", exec_frame=settings.exec_frame
        )
        self.chain = self.portal["chain"]
        for name in ("adminServer", "adminWsp", "itemType", "wspSrc", "search"):
            getattr(self.chain, name).set_session(self.session)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.session.close()

    def check_connection(self) -> dict:
        info = self.chain.adminServer.get_server_info()
        workspaces = self.list_workspaces()
        version = str(info.get("serverVersion", ""))
        return {
            "connected": True,
            "read_only": not self.settings.enable_writes,
            "writes_enabled": self.settings.enable_writes,
            "url": self.settings.url,
            "api_frame": self.settings.exec_frame,
            "server": info,
            "sdk": {
                "application": "scsuitestarter-6-5",
                "client_version": "5",
                "api_version": "6.5.3",
            },
            "compatibility": "6.5" if version.startswith("6.5") else "unverified_server_version",
            "dokiel_workspaces": workspaces["workspaces"],
        }

    def list_workspaces(self, dokiel_only: bool = True) -> dict:
        wsps = self.chain.adminWsp.list()["wsps"]
        summaries = [
            workspace_summary(w)
            for w in wsps
            if not dokiel_only or w.get("wspType", {}).get("key") == "dokiel"
        ]
        return {"workspaces": summaries, "count": len(summaries)}

    def _workspace(self, workspace: str) -> dict:
        # Require an exact code from discovery: never silently pick a similarly named workspace.
        for wsp in self.chain.adminWsp.list()["wsps"]:
            if wsp["wspCd"] == workspace:
                if wsp.get("wspType", {}).get("key") != "dokiel":
                    raise ScenariError(
                        "UNSUPPORTED_MODEL",
                        "Content discovery in this iteration targets Dokiel workspaces.",
                    )
                return wsp
        raise ScenariError(
            "WORKSPACE_NOT_FOUND", "Use an exact workspace code returned by list_workspaces."
        )

    def list_item_types(self, workspace: str, dokiel_only: bool = True) -> dict:
        wsp = self._workspace(workspace)
        types = [describe_type(t["model"], t["sgn"]) for t in self.chain.itemType.list(workspace)]
        types = [t for t in types if not dokiel_only or t["is_dokiel"]]
        types.sort(key=lambda t: t["model"] or "")
        return {
            "workspace": workspace_summary(wsp),
            "item_types": types,
            "count": len(types),
            "read_only": True,
        }

    def list_items(self, workspace: str, path: str = "/", limit: int = 50, offset: int = 0) -> dict:
        self._workspace(workspace)
        path = validate_reference(path, folder=True)
        _validate_page(limit, offset)
        result = self.chain.wspSrc.get_src_fields(
            workspace, path, [ESrcField.srcUri, ESrcField.itTi, ESrcField.itModel], depth=1
        )
        children = result.get("ch", [])
        entries = [
            {
                "path": validate_reference(c["srcUri"]),
                "title": c.get("itTi"),
                "model": c.get("itModel"),
                "is_folder": not c.get("itModel"),
            }
            for c in children
        ]
        return {
            "workspace": workspace,
            "path": path,
            "items": entries[offset : offset + limit],
            "total": len(entries),
            "next_offset": offset + limit if offset + limit < len(entries) else None,
        }

    def search_items(
        self,
        workspace: str,
        query: str = "",
        mode: str = "title",
        model: str | None = None,
        path: str = "/",
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        self._workspace(workspace)
        _validate_page(limit, offset)
        if mode not in {"title", "full_text"}:
            raise ScenariError("INVALID_SEARCH_MODE", "mode must be title or full_text.")
        if len(query) > 500:
            raise ScenariError("INVALID_QUERY", "Search text must contain at most 500 characters.")
        path = validate_reference(path, folder=True)
        criterion = build_search(query, mode, model, path)
        request = Request(criterion, number_of_results=limit + 1, start_offset=offset)
        rows = scenaripy_api.wsp_search(self.portal, workspace, request)
        items = [{"path": row[0], "title": row[1], "model": row[2]} for row in rows[:limit]]
        return {
            "workspace": workspace,
            "items": items,
            "count": len(items),
            "offset": offset,
            "next_offset": offset + limit if len(rows) > limit else None,
        }

    def read_item(self, workspace: str, reference: str) -> dict:
        self._workspace(workspace)
        reference = validate_reference(reference)
        xml = scenaripy_api.wsp_get_item(self.portal, workspace, reference)
        if not isinstance(xml, str):
            raise ScenariError("INVALID_RESPONSE", "Scenari did not return XML for this item.")
        try:
            root = SafeET.fromstring(xml)
        except Exception:
            raise ScenariError(
                "INVALID_XML",
                "The item is not valid, safe XML. "
                "Select an XML content item, rather than a folder or binary resource.",
            ) from None
        if root.tag != f"{{{SC_NS}}}item":
            raise ScenariError("NOT_AN_ITEM", "The reference does not point to a Scenari XML item.")
        links = list(
            dict.fromkeys(
                e.attrib[f"{{{SC_NS}}}refUri"]
                for e in root.iter()
                if f"{{{SC_NS}}}refUri" in e.attrib
            )
        )
        # XML is returned intact for inspecting the actual model, with a digest for future updates.
        return {
            "workspace": workspace,
            "reference": reference,
            "xml": xml,
            "sha256": hashlib.sha256(xml.encode("utf-8")).hexdigest(),
            "references": links,
            "bytes": len(xml.encode("utf-8")),
        }


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 100 or offset < 0:
        raise ScenariError(
            "INVALID_PAGINATION", "limit must be 1–100 and offset must be nonnegative."
        )
