"""Write boundaries, stale-edit detection and receipts against an HTTP API fixture."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from pydantic import ValidationError

from scenari_mcp.authoring import ITEM_ADAPTER, render_item
from scenari_mcp.client import ScenariError
from scenari_mcp.writing import AuthoringClient, ContentSession

W = "dokiel-test"


def spec(title="Original"):
    return ITEM_ADAPTER.validate_python(
        {
            "kind": "procedure",
            "title": title,
            "steps": [
                {
                    "instruction": "Inspect",
                    "details": [{"type": "remark", "paragraphs": ["Use A & B < C."]}],
                }
            ],
        }
    )


def writer(api):
    return AuthoringClient(replace(api.settings, enable_writes=True))


def test_preview_is_read_only_and_default_gate_blocks_writes(api):
    with AuthoringClient(api.settings) as c:
        preview = c.preview_item(W, spec())
        assert not preview["write_applied"]
        assert not preview["writes_enabled"]
        assert "&amp;" in preview["xml"] and "&lt;" in preview["xml"]
        assert "sp:note" in preview["xml"]
        with pytest.raises(ScenariError, match="WRITES_DISABLED"):
            c.create_item(W, "/new.unit", spec())
    assert all(method == "GET" for method, _ in api.requests)


def test_create_collision_update_and_stale_digest(api):
    with writer(api) as c:
        receipt = c.create_item(W, "/new.unit", spec())
        assert receipt["verified"] and receipt["status"] == "valid"
        assert receipt["previous_item"] is None
        first = receipt["item"]
        with pytest.raises(ScenariError, match="ALREADY_EXISTS"):
            c.create_item(W, "/new.unit", spec("Replace?"))
        update = c.update_item(W, "/new.unit", first["sha256"], spec("Updated"))
        assert update["verified"] and update["operation"] == "update"
        assert update["previous_item"] == first
        with pytest.raises(ScenariError, match="CONFLICT"):
            c.update_item(W, "/new.unit", first["sha256"], spec("Stale"))
        assert c.read_item(W, "/new.unit")["sha256"] == update["item"]["sha256"]
    assert sum(m == "PUT" for m, _ in api.requests) == 2


def test_explicit_parents_and_update_model_protection(api):
    with writer(api) as c:
        with pytest.raises(ScenariError, match="INVALID_PARENT"):
            c.create_item(W, "/NewFolder/process.unit", spec())
        result = c.create_item(W, "/NewFolder/process.unit", spec(), create_parents=True)
        assert result["verified"]
        other = ITEM_ADAPTER.validate_python(
            {"kind": "definition", "term": "Term", "paragraphs": ["Text"]}
        )
        with pytest.raises(ScenariError, match="MODEL_MISMATCH"):
            c.update_item(W, "/NewFolder/process.unit", result["item"]["sha256"], other)
        with pytest.raises(ScenariError, match="ALREADY_EXISTS"):
            c.create_item(W, "/NewFolder", spec())
        for path in ["/", "/Folder/", "/~history/item.unit", "id:target", "/a/../b"]:
            with pytest.raises(ScenariError, match="INVALID_REFERENCE"):
                c.create_item(W, path, spec())
    assert sum(m == "PUT" for m, _ in api.requests) == 1


def test_link_validation_and_server_id_normalization(api):
    def theory(ref, type="procedure"):
        return ITEM_ADAPTER.validate_python(
            {"kind": "theory", "title": "Linked", "links": [{"type": type, "reference": ref}]}
        )

    with writer(api) as c:
        with pytest.raises(ScenariError, match="BROKEN_REFERENCE"):
            c.preview_item(W, theory("/missing.unit"))
        c.create_item(W, "/process.unit", spec())
        with pytest.raises(ScenariError, match="REFERENCE_TYPE_MISMATCH"):
            c.create_item(W, "/bad.unit", theory("/process.unit", "concept"))
        api.resolve_refs = True
        result = c.create_item(W, "/linked.unit", theory("/process.unit"))
        assert result["verified"]
        assert result["item"]["references"][0].startswith("id:")
        assert result["references_checked"] == 1


def test_native_composite_image_references_are_items_but_plain_folders_are_not(api, monkeypatch):
    model, xml = render_item(spec())
    root = ET.fromstring(xml)
    image = ET.SubElement(
        root.find(".//{kelis.fr:dokiel}text"),
        "{http://www.utc.fr/ics/scenari/v3/core}extBlock",
        role="fig",
    )
    ref = "{http://www.utc.fr/ics/scenari/v3/core}refUri"
    image.set(ref, "/screenshot.png")
    with writer(api) as c:
        metadata = c._metadata

        def with_image(workspace, reference):
            if reference == "/screenshot.png":
                return {"srcSt": 2, "itModel": "sf_image", "itSt": 1, "srcId": "id:image"}
            return metadata(workspace, reference)

        monkeypatch.setattr(c, "_metadata", with_image)
        raw = ITEM_ADAPTER.validate_python(
            {"kind": "xml", "model": model, "xml": ET.tostring(root, encoding="unicode")}
        )
        assert c.preview_item(W, raw)["references"][0]["model"] == "sf_image"
        assert c.create_item(W, "/illustrated.unit", raw)["verified"]
        image.set(ref, "/Folder")
        raw.xml = ET.tostring(root, encoding="unicode")
        with pytest.raises(ScenariError, match="BROKEN_REFERENCE"):
            c.preview_item(W, raw)


@pytest.mark.parametrize(
    "state,status", [(2, "warning"), (3, "invalid"), (11, "pending"), (-99, "unknown")]
)
def test_validation_status_never_misrepresented_as_verified(api, state, status):
    api.item_status = state
    with writer(api) as c:
        result = c.create_item(W, "/unvalidated.unit", spec())
    assert result["write_applied"] is True
    assert not result["verified"] and result["status"] == status


def test_content_mismatch_and_uncertain_put_are_reported_without_retry(api):
    api.corrupt_write = True
    with writer(api) as c:
        result = c.create_item(W, "/changed.unit", spec())
        assert result["write_applied"] and not result["verified"]
        assert not result["content_matches"]
        api.put_status = 500
        failed = c.create_item(W, "/uncertain.unit", spec())
        assert failed["write_applied"] == "unknown"
        assert failed["status"] == "write_outcome_unknown"
        assert "private" not in str(failed)
    assert sum(m == "PUT" for m, _ in api.requests) == 2


def test_advanced_xml_checks_and_same_write_boundary(api):
    model, xml = render_item(spec())
    raw = ITEM_ADAPTER.validate_python({"kind": "xml", "model": model, "xml": xml})
    with writer(api) as c:
        assert c.create_item(W, "/raw.unit", raw)["verified"]
        for source, code in [
            ("<!DOCTYPE x><x/>", "INVALID_XML"),
            ("<broken>", "INVALID_XML"),
            ("<root/>", "MODEL_MISMATCH"),
            (xml.replace("dk:stepList>", "dk:concept>"), "MODEL_MISMATCH"),
        ]:
            raw.xml = source
            with pytest.raises(ScenariError, match=code):
                c.preview_item(W, raw)
        raw.xml = xml.replace("dk:stepList", "dk:notInstalled")
        raw.model = "dk_notInstalled"
        with pytest.raises(ScenariError, match="UNSUPPORTED_MODEL"):
            c.preview_item(W, raw)


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("DELETE", "wspSrc?cdaction=PutSrc"),
        ("POST", "wspSrc?cdaction=Delete"),
        ("GET", "wspSrc?cdaction=PutSrc"),
        ("PUT", "wspGen?cdaction=Generate"),
        ("PUT", "adminWsp?cdaction=PutSrc"),
        ("PUT", "wspSrc?cdaction=PutSrc&cdaction=Delete"),
    ],
)
def test_write_transport_still_blocks_unrelated_operations(api, method, suffix):
    with ContentSession(replace(api.settings, enable_writes=True)) as s:
        with pytest.raises(ScenariError, match="READ_ONLY"):
            s.request(method, api.settings.url + "/~~chain/script/u/" + suffix)
    assert not api.requests


def test_quiz_choices_are_validated_and_unknown_fields_rejected():
    quiz = {
        "kind": "single_choice_quiz",
        "question": "Question?",
        "choices": [{"label": "A", "explanation": "Why A"}, {"label": "B", "explanation": "Why B"}],
        "correct_choice": 3,
        "feedback_right": "Right",
        "feedback_wrong": "Try again",
    }
    with pytest.raises(ValidationError):
        ITEM_ADAPTER.validate_python(quiz)
    quiz["correct_choice"] = 2
    quiz["extra"] = "must not be silently discarded"
    with pytest.raises(ValidationError):
        ITEM_ADAPTER.validate_python(quiz)


def test_native_extensions_and_bibliography_round_trip(api):
    url = ITEM_ADAPTER.validate_python(
        {"kind": "web_reference", "title": "Reference", "url": "https://example.org/"}
    )
    bib = ITEM_ADAPTER.validate_python(
        {"kind": "bibliography", "identifier": "Source", "citation": "Citation"}
    )
    with writer(api) as c:
        assert c.preview_item(W, url)["recommended_extension"] == ".url"
        with pytest.raises(ScenariError, match="INVALID_EXTENSION"):
            c.create_item(W, "/website.ref", url)
        assert c.create_item(W, "/website.url", url)["verified"]
        assert c.create_item(W, "/source.ref", bib)["verified"]
