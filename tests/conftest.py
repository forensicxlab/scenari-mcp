"""A local Scenari-shaped API fixture: no calls to the user's instance."""

import base64
import hashlib
import json
import threading
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from scenari_mcp.config import Settings

ITEM_XML = """<?xml version="1.0"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xmlns:dk="kelis.fr:dokiel">
  <dk:concept><dk:conceptM/><link sc:refUri="id:linked"/>
  <link sc:refUri="id:linked"/><text>Course &amp; content</text></dk:concept>
</sc:item>"""


@pytest.fixture
def api():
    state = SimpleNamespace(
        requests=[],
        status=200,
        body=None,
        search_xml=None,
        items={},
        item_status=1,
        corrupt_write=False,
        put_status=200,
        resolve_refs=False,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            state.requests.append((self.command, self.path))
            expected = "Basic " + base64.b64encode(b"author:test-secret").decode()
            if self.headers.get("Authorization") != expected:
                self.reply(401, "private diagnostic that must never escape")
                return
            if state.status != 200:
                self.reply(state.status, "private diagnostic that must never escape")
                return
            if state.body is not None:
                self.reply(200, state.body)
                return
            url = urlsplit(self.path)
            qs = parse_qs(url.query)
            service = url.path.rsplit("/", 1)[-1]
            if service == "adminServer":
                result = {"serverName": "Fixture", "serverVersion": "6.5.4"}
            elif service == "adminWsp":
                result = {
                    "wsps": [
                        {
                            "wspCd": "dokiel-test",
                            "title": "Course",
                            "status": "ok",
                            "wspType": {"key": "dokiel", "version": "26.0.3", "lang": "en-US"},
                            "wspOptions": [{"key": "dokielTraining"}],
                        },
                        {"wspCd": "other-test", "title": "Other", "wspType": {"key": "Opale"}},
                    ]
                }
            elif service == "itemType":
                self.reply(
                    200,
                    '<listSs xmlns="scenari">'
                    '<ss model="dk_stepList" sgn="@dk_stepList#Xml"/>'
                    '<ss model="dk_exercise" sgn="@dk_exercise#Xml"/>'
                    '<ss model="dk_custom" sgn="@dk_custom#Xml"/>'
                    + "".join(
                        f'<ss model="dk_{m}" sgn="@dk_{m}#Xml"/>'
                        for m in [
                            "definition",
                            "bib",
                            "url",
                            "concept",
                            "theory",
                            "mcqSur",
                            "eval",
                            "module",
                            "tutorial",
                            "tutorialRoot",
                        ]
                    )
                    + '<ss model="sf_image" sgn="@sf_image#Binary"/><ss/></listSs>',
                )
                return
            elif service == "search":
                state.search_xml = qs["request"][0]
                request = ET.fromstring(state.search_xml)
                select = request.find("select")
                start = int(select.attrib["startOffset"])
                size = int(select.attrib["max"])
                rows = [[f"/topic{i}.unit", f"Topic {i}", "dk_concept"] for i in range(5)]
                result = {
                    "columns": ["srcUri", "itTi", "itModel"],
                    "results": rows[start : start + size],
                }
            elif service == "wspSrc":
                ref = qs.get("refUri", [""])[0]
                if qs.get("fields") and qs.get("depth") == ["0"]:
                    if ref.startswith("id:"):
                        ref = next((r for r in state.items if item_id(r) == ref), ref)
                    if ref in state.items:
                        root = ET.fromstring(state.items[ref])
                        result = {
                            "srcUri": ref,
                            "srcSt": 1,
                            "srcId": item_id(ref),
                            "itModel": "dk_" + root[0].tag.split("}")[1],
                            "itSt": state.item_status,
                        }
                    elif ref in {"/", "/Folder"} or any(
                        r.startswith(ref + "/") for r in state.items
                    ):
                        result = {"srcUri": ref, "srcSt": 2}
                    else:
                        result = {"srcUri": ref, "srcSt": -1, "itSt": -1}
                    self.reply(200, json.dumps(result))
                    return
                if ref in state.items:
                    self.reply(200, state.items[ref])
                    return
                if ref == "/missing.unit":
                    self.reply(404, "private missing-item diagnostic")
                    return
                if qs.get("format") == ["JSON"]:
                    result = {
                        "srcUri": "/",
                        "ch": [
                            {"srcUri": "//Folder"},
                            {"srcUri": "//topic.unit", "itTi": "Topic", "itModel": "dk_concept"},
                        ],
                    }
                else:
                    self.reply(200, ITEM_XML)
                    return
            else:
                self.reply(404, "not found")
                return
            self.reply(200, json.dumps(result))

        def do_PUT(self):
            state.requests.append((self.command, self.path))
            data = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            if state.put_status != 200:
                self.reply(state.put_status, "private failure")
                return
            qs = parse_qs(urlsplit(self.path).query)
            assert qs["cdaction"] == ["PutSrc"]
            state.items[qs["refUri"][0]] = (
                data.replace("Original", "Changed") if state.corrupt_write else data
            )
            root = ET.fromstring(state.items[qs["refUri"][0]])
            if root[0].tag.split("}")[1] in {"bib", "tutorialRoot"}:
                root.set("version", "1")
                state.items[qs["refUri"][0]] = ET.tostring(root, encoding="unicode")
            if state.resolve_refs:
                ref = qs["refUri"][0]
                root = ET.fromstring(state.items[ref])
                for node in root.iter():
                    key = "{http://www.utc.fr/ics/scenari/v3/core}refUri"
                    if key in node.attrib:
                        node.set(key, item_id(node.attrib[key]))
                state.items[ref] = ET.tostring(root, encoding="unicode")
            self.reply(200, "")

        def reply(self, status, body):
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def item_id(path):
        return "id:" + hashlib.sha256(path.encode()).hexdigest()[:12]

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    state.settings = Settings(
        f"http://127.0.0.1:{httpd.server_port}/scenari", "author", "test-secret"
    )
    try:
        yield state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
