import http.server
import urllib.request
from http import HTTPStatus

from pytest_pyodide.server import spawn_web_server


def test_spawn_web_server_with_params(tmp_path):

    (tmp_path / "index.txt").write_text("a")
    extra_headers = {"Custom-Header": "42"}
    with spawn_web_server(tmp_path, extra_headers=extra_headers) as (
        hostname,
        port,
        log_path,
    ):
        res = urllib.request.urlopen(f"http://{hostname}:{port}/index.txt")
        assert res.status == 200
        assert res.headers
        assert res.read() == b"a"
        assert res.headers["Access-Control-Allow-Origin"] == "*"
        assert res.headers.get("Custom-Header") == "42"


class HelloWorldHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(b"hello world")


def test_custom_handler(tmp_path):
    with spawn_web_server(tmp_path, handler_cls=HelloWorldHandler) as server:
        hostname, port, _ = server
        res = urllib.request.urlopen(f"http://{hostname}:{port}/index.txt")
        assert res.status == 200
        assert res.read() == b"hello world"
