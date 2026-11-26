"""Explicit content writes, with preconditions and honest post-write receipts."""

import hashlib
import re
import threading
import xml.etree.ElementTree as ET

from defusedxml import ElementTree as SafeET
from scsuitestarter_6_5.api.item import ESrcField as F

from .authoring import DK_NS, REF, SC_NS, SP_NS, SPACE, ItemSpec, render_item
from .client import ReadOnlySession, ScenariClient, ScenariError, validate_reference

# Serialize this process's read/check/write sequences. External editors are not locked.
WRITE_LOCK = threading.RLock()
QUIZZES = {"dk_mcqSur", "dk_mcqMur", "dk_field", "dk_numerical", "dk_cloze", "dk_order", "dk_match"}
EXTENSIONS = {
    "dk_definition": ".ref",
    "dk_bib": ".ref",
    "dk_url": ".url",
    "dk_concept": ".unit",
    "dk_stepList": ".unit",
    "dk_theory": ".unit",
    "dk_exercise": ".unit",
    "dk_mcqSur": ".quiz",
    "dk_eval": ".scen",
    "dk_module": ".scen",
    "dk_tutorial": ".scen",
    "dk_tutorialRoot": ".pub",
}
SLOTS = {
    ("concept", "def"): {"dk_definition"},
    ("content", "def"): {"dk_concept"},
    ("content", "op"): {"dk_stepList"},
    ("eval", "quiz"): QUIZZES,
    ("module", "theory"): {"dk_theory"},
    ("module", "exercise"): {"dk_exercise"},
    ("tutorial", "module"): {"dk_module"},
    ("tutorial", "eval"): {"dk_eval"},
    ("tutorialRoot", "content"): {"dk_tutorial", "dk_module", "dk_eval"},
}


class ContentSession(ReadOnlySession):
    """Add only wspSrc/PutSrc; no delete, publish, permissions or arbitrary HTTP."""

    content_writes = True


def write_path(value: str) -> str:
    path = validate_reference(value, folder=True)
    if path == "/" or value.endswith("/") or path.startswith("/~"):
        raise ScenariError("INVALID_REFERENCE", "Use a normal absolute item path, not a folder.")
    return path


def semantic_tree(node, ids):
    """Ignore serializer prefixes/indentation; retain text, order and meaningful attributes."""
    attrs = tuple(sorted((k, ids.get(v, v) if k == REF else v) for k, v in node.attrib.items()))
    preserve = node.attrib.get(SPACE) == "preserve"
    text = node.text or ""
    if len(node) and not text.strip() and not preserve:
        text = ""
    children = []
    for child in node:
        tail = child.tail or ""
        if not tail.strip() and not preserve:
            tail = ""
        children.append((semantic_tree(child, ids), tail))
    return node.tag, attrs, text, tuple(children)


class AuthoringClient(ScenariClient):
    session_type = ContentSession

    def read_item(self, workspace: str, reference: str) -> dict:
        result = super().read_item(workspace, reference)
        meta = self._metadata(workspace, reference)
        state = meta.get("itSt")
        result.update(
            model=meta.get("itModel"),
            server_item_status=state,
            status={1: "valid", 2: "warning", 3: "invalid", 11: "pending"}.get(state, "unknown"),
        )
        return result

    def _metadata(self, workspace, reference):
        try:
            result = self.chain.wspSrc.get_src_fields(
                workspace, reference, [F.srcUri, F.srcSt, F.srcId, F.itModel, F.itSt], depth=0
            )
        except ScenariError as exc:
            if exc.code == "NOT_FOUND":
                return {"srcSt": -1}
            raise
        if result.get("srcSt") not in {-1, 1, 2}:
            raise ScenariError("INVALID_RESPONSE", "Scenari did not return a resource status.")
        return result

    def _prepare(self, workspace, item):
        self._workspace(workspace)
        model, xml = render_item(item)
        if len(xml.encode()) > self.settings.max_item_bytes:
            raise ScenariError("ITEM_TOO_LARGE", "XML exceeds SCENARI_MAX_ITEM_BYTES.")
        try:
            if "<!DOCTYPE" in xml.upper():
                raise ValueError("DTD")
            root = SafeET.fromstring(xml)
        except Exception:
            raise ScenariError(
                "INVALID_XML", "Supply well-formed XML without DTDs or entities."
            ) from None
        if (
            root.tag != f"{{{SC_NS}}}item"
            or len(root) != 1
            or root[0].tag != f"{{{DK_NS}}}{model.removeprefix('dk_')}"
        ):
            raise ScenariError(
                "MODEL_MISMATCH", "XML must contain one sc:item child matching the Dokiel model."
            )
        installed = {t["model"] for t in self.chain.itemType.list(workspace)}
        if model not in installed:
            raise ScenariError("UNSUPPORTED_MODEL", "The requested item model is not installed.")
        refs = {}
        ids = {}
        for parent in root.iter():
            for node in parent:
                if REF not in node.attrib:
                    continue
                ref = validate_reference(node.attrib[REF])
                node.set(REF, ref)
                if ref not in refs:
                    meta = self._metadata(workspace, ref)
                    # Binary resources such as sf_image are composite items: srcSt=2
                    # at their root, with a native model. Plain folders have no model.
                    if meta["srcSt"] not in {1, 2} or not meta.get("itModel"):
                        raise ScenariError("BROKEN_REFERENCE", f"Not an existing item: {ref}")
                    if meta.get("itSt") not in {1, 2}:
                        raise ScenariError(
                            "INVALID_LINKED_ITEM",
                            f"Linked item is invalid or not yet validated: {ref}",
                        )
                    refs[ref] = meta
                    if meta.get("srcId"):
                        ids[ref] = meta["srcId"]
                expected = None
                if parent.tag.startswith(f"{{{DK_NS}}}") and node.tag.startswith(f"{{{SP_NS}}}"):
                    expected = SLOTS.get((parent.tag.split("}")[1], node.tag.split("}")[1]))
                if expected and refs[ref].get("itModel") not in expected:
                    raise ScenariError(
                        "REFERENCE_TYPE_MISMATCH",
                        f"The linked item's model is wrong for its slot: {ref}",
                    )
        # Normalize references in the submitted XML as well as the comparison tree.
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        return model, xml, root, refs, ids

    def preview_item(self, workspace: str, item: ItemSpec) -> dict:
        model, xml, _, refs, _ = self._prepare(workspace, item)
        return {
            "workspace": workspace,
            "model": model,
            "recommended_extension": EXTENSIONS.get(model),
            "xml": xml,
            "sha256": hashlib.sha256(xml.encode()).hexdigest(),
            "bytes": len(xml.encode()),
            "references": [{"reference": r, "model": m.get("itModel")} for r, m in refs.items()],
            "writes_enabled": self.settings.enable_writes,
            "write_applied": False,
            "validation": "Local structure, installed model and existing links checked. "
            "Full Dokiel validation is performed by Scenari after saving.",
        }

    def create_item(
        self, workspace: str, path: str, item: ItemSpec, create_parents: bool = False
    ) -> dict:
        return self._write(workspace, path, item, create_parents=create_parents)

    def update_item(
        self, workspace: str, reference: str, expected_sha256: str, item: ItemSpec
    ) -> dict:
        if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
            raise ScenariError("INVALID_DIGEST", "Use the SHA-256 returned by read_item.")
        return self._write(workspace, reference, item, expected_sha256=expected_sha256)

    def _write(self, workspace, reference, item, *, create_parents=False, expected_sha256=None):
        if not self.settings.enable_writes:
            raise ScenariError("WRITES_DISABLED", "Set SCENARI_ENABLE_WRITES=true and reconnect.")
        reference = (
            write_path(reference) if expected_sha256 is None else validate_reference(reference)
        )
        with WRITE_LOCK:
            model, xml, root, refs, ids = self._prepare(workspace, item)
            meta = self._metadata(workspace, reference)
            before = None
            if expected_sha256 is None:
                reference = write_path(reference)
                if meta["srcSt"] != -1:
                    raise ScenariError(
                        "ALREADY_EXISTS", "Creation never replaces an existing resource."
                    )
                extension = EXTENSIONS.get(model)
                if extension and not reference.endswith(extension):
                    raise ScenariError(
                        "INVALID_EXTENSION",
                        f"Use {extension} for this native model; the path "
                        "affects Scenari's model recognition.",
                    )
                parent = reference.rsplit("/", 1)[0] or "/"
                while True:
                    parent_meta = self._metadata(workspace, parent)
                    if parent_meta["srcSt"] == 2:
                        break
                    if parent_meta["srcSt"] != -1 or not create_parents or parent == "/":
                        raise ScenariError(
                            "INVALID_PARENT",
                            "Parent must be an existing folder; "
                            "use create_parents only for intentional new folders.",
                        )
                    parent = parent.rsplit("/", 1)[0] or "/"
            else:
                if meta["srcSt"] != 1:
                    raise ScenariError("NOT_FOUND", "Updates require an existing XML item.")
                # Resolve id: references to a normal path; reject special history/trash contexts.
                reference = write_path(meta.get("srcUri", reference))
                if meta.get("itModel") != model:
                    raise ScenariError(
                        "MODEL_MISMATCH", "Updates must retain the existing item model."
                    )
                before = self.read_item(workspace, reference)
                if before["sha256"] != expected_sha256:
                    raise ScenariError(
                        "CONFLICT", "Item changed. Read it and review the changes before updating."
                    )
            # No automatic retries: an interrupted PUT may already have been applied.
            try:
                self.chain.wspSrc.put_src(workspace, reference, xml)
            except Exception as exc:
                return {
                    "workspace": workspace,
                    "reference": reference,
                    "model": model,
                    "write_applied": "unknown",
                    "verified": False,
                    "status": "write_outcome_unknown",
                    "error_code": exc.code if isinstance(exc, ScenariError) else "INVALID_RESPONSE",
                    "message": "The PUT did not complete normally. Read this path before retrying; "
                    "the server may have saved it. No automatic retry was attempted.",
                    "previous_item": before,
                }
            try:
                saved = self.read_item(workspace, reference)
                saved_meta = self._metadata(workspace, reference)
                # Scenari resolves paths to IDs. Check saved references against the same IDs.
                for ref in saved["references"]:
                    if ref not in ids:
                        linked = self._metadata(workspace, ref)
                        if linked.get("srcId"):
                            ids[ref] = linked["srcId"]
                matches = semantic_tree(root, ids) == semantic_tree(
                    SafeET.fromstring(saved["xml"]), ids
                )
                state = saved_meta.get("itSt")
                status = {1: "valid", 2: "warning", 3: "invalid", 11: "pending"}.get(
                    state, "unknown"
                )
                verified = matches and saved_meta.get("itModel") == model and state == 1
                return {
                    "workspace": workspace,
                    "reference": reference,
                    "model": model,
                    "operation": "update" if before else "create",
                    "write_applied": True,
                    "verified": verified,
                    "status": status,
                    "server_item_status": state,
                    "saved_model": saved_meta.get("itModel"),
                    "content_matches": matches,
                    "item": saved,
                    "previous_item": before,
                    "references_checked": len(refs),
                    "concurrency": "Preflight digest/existence checks; not an atomic server lock.",
                }
            except Exception:
                return {
                    "workspace": workspace,
                    "reference": reference,
                    "model": model,
                    "write_applied": True,
                    "verified": False,
                    "status": "verification_failed",
                    "message": "Scenari accepted the PUT, but read-back verification failed. "
                    "Read this item before continuing. No retry or rollback was attempted.",
                    "previous_item": before,
                }
