from pathlib import Path

from pytest_pyodide import run_in_pyodide, spawn_web_server


@run_in_pyodide(packages=["micropip"])
async def test_install_from_pypi(selenium_standalone):
    import micropip

    await micropip.install("snowballstemmer==2.2.0")

    import snowballstemmer

    stemmer = snowballstemmer.stemmer("english")
    assert stemmer.stemWords(["university"]) == ["univers"]


def test_install_from_custom_server(selenium_standalone):
    with spawn_web_server(Path(__file__).parent / "wheels") as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        url = base_url + "snowballstemmer-2.2.0-py2.py3-none-any.whl"

        selenium = selenium_standalone
        selenium.run_js(
            f"""
            await pyodide.loadPackage({url!r});
            """
        )
        selenium.run(
            """
            import snowballstemmer
            stemmer = snowballstemmer.stemmer('english')
            assert stemmer.stemWords(["university"]) == ["univers"]
            """
        )
