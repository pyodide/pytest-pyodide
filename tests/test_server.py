import http.server
from http import HTTPStatus

import requests

from pytest_pyodide.server import _default_templates, spawn_web_server


def test_spawn_web_server_with_params(tmp_path):
    (tmp_path / "index.txt").write_text("a")
    extra_headers = {"Custom-Header": "42"}
    with spawn_web_server(tmp_path, extra_headers=extra_headers) as (
        hostname,
        port,
        log_path,
    ):
        res = requests.get(f"http://{hostname}:{port}/index.txt")
        assert res.ok
        assert res.headers
        assert res.content == b"a"
        assert res.headers["Access-Control-Allow-Origin"] == "*"
        assert res.headers.get("Custom-Header") == "42"


def test_spawn_web_server_default_templates(tmp_path):
    default_templates = _default_templates()

    with spawn_web_server(tmp_path) as (hostname, port, _):
        for path, content in default_templates.items():
            res = requests.get(f"http://{hostname}:{port}{path}")
            assert res.ok
            assert res.headers
            assert res.content == content
            assert res.headers["Access-Control-Allow-Origin"] == "*"


class HelloWorldHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(b"hello world")


def test_custom_handler(tmp_path):
    with spawn_web_server(tmp_path, handler_cls=HelloWorldHandler) as server:
        hostname, port, _ = server
        res = requests.get(f"http://{hostname}:{port}/index.txt")
        assert res.ok
        assert res.content == b"hello world"
