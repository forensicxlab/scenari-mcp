import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
import requests

from scenari_mcp.client import ReadOnlySession, ScenariClient, ScenariError, build_search


def test_discovery_uses_actual_version_and_workspace_types(api):
    with ScenariClient(api.settings) as client:
        status = client.check_connection()
        assert status["server"]["serverVersion"] == "6.5.4"
        assert status["compatibility"] == "6.5"
        assert status["read_only"] is True
        assert len(status["dokiel_workspaces"]) == 1
        assert client.list_workspaces(dokiel_only=False)["count"] == 2
        catalog = client.list_item_types("dokiel-test")
        models = {item["model"]: item for item in catalog["item_types"]}
        assert {"dk_stepList", "dk_exercise", "dk_custom"} <= set(models)
        assert models["dk_stepList"]["label"] == "Procedure"
        assert "label" not in models["dk_custom"]  # Unknown installed types remain visible.
    assert all(method == "GET" for method, _ in api.requests)


def test_folder_and_search_pagination(api):
    with ScenariClient(api.settings) as client:
        page = client.list_items("dokiel-test", limit=1)
        assert page["items"][0] == {
            "path": "/Folder",
            "title": None,
            "model": None,
            "is_folder": True,
        }
        assert page["next_offset"] == 1
        assert client.list_items("dokiel-test", limit=1, offset=1)["next_offset"] is None
        page = client.search_items("dokiel-test", limit=2)
        assert len(page["items"]) == 2
        assert page["next_offset"] == 2
        last = client.search_items("dokiel-test", limit=2, offset=4)
        assert len(last["items"]) == 1
        assert last["next_offset"] is None


def test_item_xml_and_reference_round_trip(api):
    with ScenariClient(api.settings) as client:
        result = client.read_item("dokiel-test", "id:existing")
        assert result["references"] == ["id:linked"]
        assert result["sha256"] == hashlib.sha256(result["xml"].encode()).hexdigest()
        assert result["bytes"] == len(result["xml"].encode())


@pytest.mark.parametrize("mode", ["title", "full_text"])
def test_search_quotes_are_data_and_criteria_are_scoped(mode):
    query = 'a"/><exp type="Injected"/> & < [test]'
    xml = build_search(query, mode, "dk_concept", '/Course "A"').serialize()
    root = ET.fromstring(xml)
    assert [el.attrib["type"] for el in root] == [
        "Items",
        "ItemCodeOrTitle" if mode == "title" else "FullText",
        "ItemModel",
    ]
    assert root[0].attrib["afterUri"] == '/Course "A"/'
    assert root[0].attrib["beforeEndFolder"] == '/Course "A"/'
    if mode == "full_text":
        assert root[1].attrib["textSearch"] == query
    else:
        assert r"\[test\]" in root[1].attrib["regexp"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "HEAD"])
def test_transport_blocks_write_verbs_before_network(api, method):
    with ReadOnlySession(api.settings) as session, pytest.raises(ScenariError, match="READ_ONLY"):
        session.request(method, api.settings.url + "/~~chain/script/u/wspSrc")
    assert not api.requests


@pytest.mark.parametrize(
    "suffix",
    [
        "adminWsp?cdaction=DeleteWsp",
        "wspSrc?cdaction=Delete",
        "adminUsers?cdaction=List",
        "adminWsp?cdaction=List&cdaction=DeleteWsp",
    ],
)
def test_transport_blocks_unsafe_gets(api, suffix):
    with ReadOnlySession(api.settings) as session, pytest.raises(ScenariError, match="READ_ONLY"):
        session.get(api.settings.url + "/~~chain/script/u/" + suffix)
    assert not api.requests


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "AUTHENTICATION_FAILED"),
        (403, "ACCESS_DENIED"),
        (404, "NOT_FOUND"),
        (500, "HTTP_ERROR"),
        (302, "REDIRECT"),
    ],
)
def test_api_errors_are_safe_and_redirects_not_followed(api, status, code):
    api.status = status
    with ScenariClient(api.settings) as client, pytest.raises(ScenariError, match=code) as caught:
        client.check_connection()
    assert "private" not in str(caught.value)
    assert "test-secret" not in str(caught.value)
    assert len(api.requests) == 1


def test_size_limit_and_unsafe_xml(api):
    api.body = "x" * 1025
    with (
        ScenariClient(replace(api.settings, max_item_bytes=1024)) as client,
        pytest.raises(ScenariError, match="RESPONSE_TOO_LARGE"),
    ):
        client.check_connection()
    api.body = None
    with ScenariClient(api.settings) as client:
        # Return hostile XML only for the item fetch, after workspace discovery.
        client._workspace = lambda _: {}
        api.body = '<!DOCTYPE x [<!ENTITY entity "expansion">]><x>&entity;</x>'
        with pytest.raises(ScenariError, match="INVALID_XML"):
            client.read_item("dokiel-test", "/bad.unit")


def test_timeout_redacts_exception_and_is_bounded(api, monkeypatch):
    def fail(*_, **kwargs):
        assert kwargs["timeout"] == api.settings.timeout_seconds
        raise requests.exceptions.Timeout("private test-secret")

    monkeypatch.setattr(requests.Session, "send", fail)
    with (
        ScenariClient(api.settings) as client,
        pytest.raises(ScenariError, match="TIMEOUT") as caught,
    ):
        client.check_connection()
    assert "private" not in str(caught.value)


def test_rejects_unknown_workspace_non_dokiel_and_invalid_inputs(api):
    with ScenariClient(api.settings) as client:
        for workspace, code in [
            ("Course", "WORKSPACE_NOT_FOUND"),
            ("other-test", "UNSUPPORTED_MODEL"),
        ]:
            with pytest.raises(ScenariError, match=code):
                client.list_items(workspace)
        for path in ["relative.unit", "/a/../b", "https://host/file", "/bad\x00.unit"]:
            with pytest.raises(ScenariError, match="INVALID_REFERENCE"):
                client.read_item("dokiel-test", path)
        with pytest.raises(ScenariError, match="INVALID_PAGINATION"):
            client.search_items("dokiel-test", limit=101)
