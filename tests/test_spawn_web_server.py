from http import HTTPStatus

from pytest_pyodide import spawn_web_server
from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.server import DefaultHandler


class CustomHandler(DefaultHandler):
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(b"hello world")


def test_custom_handler(selenium):
    @run_in_pyodide
    async def inner_function(selenium, base_url):
        from js import fetch
        response = await fetch(base_url + "/random-path")
        return await response.text()

    with spawn_web_server(".", handler_cls=CustomHandler) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"

        data = inner_function(selenium, base_url)
        assert data == "hello world"
