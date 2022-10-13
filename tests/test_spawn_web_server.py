from multiprocessing import Queue

from pytest_pyodide import spawn_web_server
from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.server import DefaultHandler


class CustomHeaderHandler(DefaultHandler):
    q: Queue

    # def do_POST(self):
    #     return None

    def end_headers(self):
        print(self.request)
        self.send_header("Access-Control-Expose-Headers", "Custom-Header")
        self.send_header("Custom-Header", "test")
        super().end_headers()




def test_spawn_web_server(selenium):
    print("running test")
    selenium.run_js(
        f"""
        await pyodide.loadPackage("micropip");
        """
    )
    selenium.run_async(f'import micropip\nawait micropip.install("requests")\nawait micropip.install("pyodide-http")')
    selenium.run(
        """
        import pyodide_http
        pyodide_http.patch_all()

        """
    )

    @run_in_pyodide
    async def inner_function(selenium, base_url):
        print("hi")
        try:
            import requests
        except ImportError:
            print("not found")
            return
        print("blaat")
        data = requests.get(
            base_url + "blaat"
        )
        return data
        # from js import fetch
        # from pyodide import to_js
        # data = await fetch(base_url + "blaat", to_js({"method": "POST", "body": "piet", "mode": "cors"}))
        # return dict(data.headers.to_py())

    # CustomHeaderHandler.q = Queue()

    with spawn_web_server(".") as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"

        headers = inner_function(selenium, base_url)
        assert headers['custom-header'] == 'test'
    #
    # while True:
    #     item = CustomHeaderHandler.q.get(block=False)
    #     if not item:
    #         break
    #     print(item)

