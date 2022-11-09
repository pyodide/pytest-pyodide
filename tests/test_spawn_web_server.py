from http import HTTPStatus

from pytest_pyodide import spawn_web_server
from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.server import DefaultHandler


class HelloWorldHandler(DefaultHandler):
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(b"hello world")


def test_custom_handler(selenium):
    @run_in_pyodide
    async def inner_function(selenium, base_url):
        from pyodide.http import pyfetch

        data = await pyfetch(base_url + "/random-path")
        return await data.string()

    with spawn_web_server(".", handler_cls=HelloWorldHandler) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"

        data = inner_function(selenium, base_url)
        assert data == "hello world"


class EchoHandler(DefaultHandler):
    def do_POST(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()

        content_len = int(self.headers.get("content-length", 0))
        post_body = self.rfile.read(content_len)
        self.wfile.write(post_body)

    def do_GET(self) -> None:
        # A client should not send a GET request
        self.send_response(HTTPStatus.BAD_REQUEST)
        self.end_headers()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "POST")

        super().end_headers()

    def do_OPTIONS(self):
        # When sending sync POST requests with custom headers
        # like "Content-Type" chrome will send a preflight
        # OPTIONS request. Make sure to handle it correctly.
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()


def test_post_handler(selenium):
    @run_in_pyodide
    async def inner_function(selenium, base_url):
        from js import fetch, eval, require
        from pyodide import to_js

        https = require('https')
        req = https.request({'method': 'POST'})
        req.write("hi")
        req.end()
                            # print(f"Data: {await data.text()}")
        # return "blaat"
        #
        # data = await fetch(
        #     base_url + "random-path",
        #     to_js(dict(method="post", body="some post data"))
        # )
        print(data.status)
        print(data.statusText)
        return await data.text()

    with spawn_web_server(".", handler_cls=EchoHandler) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"

        data = inner_function(selenium, base_url)
        assert data == "some post data"
