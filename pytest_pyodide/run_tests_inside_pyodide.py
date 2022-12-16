from pathlib import Path
from typing import Any, ContextManager

import pytest

from .server import spawn_web_server

_seleniums: dict[str, list[Any]] = {}
_copied_files = []
_playwright_browsers = None


class ContextManagerUnwrapper:
    """Class to take a context manager (e.g. a pytest fixture or something)
    and unwrap it so that it can be used for the whole of the module.

    This is a bit of a hack, but it allows us to use some of our pytest fixtures
    without having to be inside a pytest context. Avoids significant duplication
    of the standard pytest_pyodide code here.
    """

    def __init__(self, ctx_manager: ContextManager):
        self.ctx_manager = ctx_manager
        self.value = ctx_manager.__enter__()

    def get_value(self):
        return self.value

    def __del__(self):
        self.close()

    def close(self):
        if self.ctx_manager is not None:
            self.ctx_manager.__exit__(None, None, None)
            self.value = None


def start_pyodide_in_browser(request: pytest.FixtureRequest, runtime: str):
    """Start a browser running with pyodide, ready to run pytest
    calls. If the same runtime is already running, it will
    just return that.
    """
    global _playwright_browsers
    from .fixture import playwright_browsers, selenium_common

    if request.config.option.runner.lower == "playwright":
        _playwright_browsers = playwright_browsers(request)
    if runtime in _seleniums:
        return _seleniums[runtime][0].get_value()
    web_server_main = ContextManagerUnwrapper(
        spawn_web_server(request.config.option.dist_dir)
    )
    # open pyodide
    _seleniums[runtime] = [
        ContextManagerUnwrapper(
            selenium_common(
                request,
                runtime,
                web_server_main.get_value(),
                browsers=_playwright_browsers,
            )
        ),
        web_server_main,
    ]
    return _seleniums[runtime][0].get_value()


def copy_files_to_emscripten_fs(
    file_list: list[Path], request: pytest.FixtureRequest, runtime: str
):
    """
    Copies files in file_list to the emscripten file system. Files
    go into the test_files subfolder on emscripten. They are transferred
    using pyfetch and a web-server.
    """
    new_files = []
    for x in file_list:
        if x.is_dir():
            continue
        if x not in _copied_files:
            new_files.append(x.resolve())
    if len(new_files) == 0:
        return
    base_path = Path.cwd()
    selenium = start_pyodide_in_browser(request, runtime)
    with spawn_web_server(base_path) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        # fetch all files into the pyodide
        # n.b. this might be slow for big packages
        selenium.run(
            """
            from pyodide.http import pyfetch
            all_fetches = []
            all_wheels = []
            """
        )
        for file in new_files:
            _copied_files.append(file)
            file_url = base_url + str(file.relative_to(base_path))
            if file.suffix == ".whl":
                # wheel - install the wheel on the pyodide side before
                # any fetches
                selenium.run_async(
                    f"""
                    all_wheels.append("{file_url}")
                    """
                )
            else:
                # add file to fetches
                selenium.run_async(
                    f"""
                    all_fetches.append(pyfetch("{file_url}"))
                    """
                )
        # install all wheels with micropip
        selenium.run_async(
            """
            import micropip
            await micropip.install(all_wheels)
            """
        )
        # fetch everything all at once
        selenium.run_async(
            """
            import asyncio, os, os.path

            for coro in asyncio.as_completed(all_fetches):
                response = await coro
                bare_path = "/".join(response.url.split("/")[3:])
                write_path = "./test_files/" + bare_path
                os.makedirs(os.path.dirname(write_path), exist_ok=True)
                with open(write_path, "wb") as fp:
                    byte_data = await response.bytes()
                    fp.write(byte_data)
            """
        )


def run_test_in_pyodide(node_tree_id, runtime, ignore_fail=False):
    """This runs a single test (identified by node_tree_id) inside
    the pyodide runtime. How it does it is by calling pytest on the
    browser pyodide with the full node ID, which is the same
    as it is locally except for the test_files folder base.

    It also has a little bit of cunning which reformats the output
    from the pyodide call to pytest, so that test failures should look
    roughly the same as they would when you are running pytest locally.
    """
    selenium = _seleniums[runtime][0].get_value()
    all_args = ["./test_files/" + node_tree_id, "--color=no"]
    ret_error = selenium.run_async(
        f"""
        import pytest

        out_buf = ""

        def write_out(line):
            global out_buf
            out_buf += line

        import sys

        sys.stdout.write = write_out
        sys.stderr.write = write_out
        print("{all_args}")
        retcode = pytest.main({all_args})
        if retcode == 0:
            out_buf = ""
        out_buf
        """
    )
    # This reformats the error as it is output by pytest inside
    # pyodide, so that we don't see all the setup / teardown stuff,
    # and also so that colouring, stdout / stderr capturing works
    # as you would expect.
    #
    # Without this reformatting, you get a whole load too much stuff printed
    # out in the case of a test fail.
    if len(ret_error) != 0:
        print("ERR:", ret_error, "\n*******************")
        ret_error_lines = ret_error.splitlines()
        fail_error = []
        fail_stdout = []
        recording_error = False
        recording_stdout = False
        for line in ret_error_lines:
            if line.find(" FAILURES ") != -1:
                recording_error = True
            elif line.find("Captured stdout") != -1:
                recording_stdout = True
                recording_error = False
            elif line.find("========= short test summary") != -1:
                recording_error = False
                recording_stdout = False
            elif recording_error:
                fail_error.append(line)
            elif recording_stdout:
                fail_stdout.append(line)
        print("\n".join(fail_stdout))
        if not ignore_fail:
            pytest.fail("\n".join(fail_error[1:]), pytrace=False)
        return False
    return True


def close_inside_pyodide_browsers():
    """Close the browsers that are currently open with
    pyodide runtime initialised.

    This is done at the end of testing so that we can run more
    than one test without launching browsers each time.
    """
    global _seleniums
    for x in _seleniums.values():
        x[0].close()
    del _seleniums
