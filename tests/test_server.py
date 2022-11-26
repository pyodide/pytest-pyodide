import urllib.request

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
        assert res.headers.get("Custom-Header") == "42"
