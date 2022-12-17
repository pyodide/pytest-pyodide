import re
import sys
import xml.etree.ElementTree as ET
from typing import Any, ContextManager

import pytest

from .server import spawn_web_server

_seleniums: dict[str, list[Any]] = {}
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


def get_browser_pyodide(request: pytest.FixtureRequest, runtime: str):
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


def _remove_pytest_capture_title(
    capture_element: ET.Element | None, title_name: str
) -> str | None:
    """
    pytest captures (even in xml) have a title line
    like ------ Capture out -------

    This helper removes that line.
    """
    if not capture_element:
        return None
    capture_text = capture_element.text
    if not capture_text:
        return None
    lines = capture_text.splitlines()
    if lines[0].find(" " + title_name + " "):
        ret_data = "\n".join(lines[1:])
        if re.search(r"\S", ret_data):
            return ret_data
        else:
            return None
    return "\n".join(lines)


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
    all_args = [
        node_tree_id,
        "--color=no",
        "--junitxml",
        "test_output.xml",
        "-o",
        "junit_logging=out-err",
    ]
    ret_xml = selenium.run_async(
        f"""
        import pytest
        retcode = pytest.main({all_args})

        output_xml=""
        with open("test_output.xml","r") as f:
            output_xml=f.read()
        output_xml
        """
    )
    # get the error from junitxml
    with open("test.xml", "w") as f:
        f.write(ret_xml)
    root = ET.fromstring(ret_xml)
    fails = root.findall("*/testcase[failure]")
    for fail in fails:
        stdout = fail.find("./system-out")
        stderr = fail.find("./system-err")
        failure = fail.find("failure")
        if failure and failure.text:
            fail_txt = failure.text
        else:
            fail_txt = ""
        stdout_text = _remove_pytest_capture_title(stdout, "Captured Out")
        stderr_text = _remove_pytest_capture_title(stderr, "Captured Err")
        if stdout:
            print(stdout_text)
        if stderr_text:
            sys.stderr.write(stderr_text)
        if not ignore_fail:

            pytest.fail(fail_txt, pytrace=False)
        return False
    return True


def close_pyodide_browsers():
    """Close the browsers that are currently open with
    pyodide runtime initialised.

    This is done at the end of testing so that we can run more
    than one test without launching browsers each time.
    """
    global _seleniums
    for x in _seleniums.values():
        x[0].close()
    del _seleniums
