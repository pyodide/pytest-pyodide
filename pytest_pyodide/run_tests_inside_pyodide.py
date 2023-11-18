import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from .copy_files_to_pyodide import copy_files_to_emscripten_fs


def run_in_pyodide_generate_tests(metafunc):
    metafunc.fixturenames += ("runtime", "selenium")
    metafunc.parametrize("runtime", pytest.pyodide_runtimes, scope="module")


def copy_files(selenium, path: Path):
    # Pass this test to pyodide runner
    # First: make sure that pyodide has the test folder copied over
    copy_files = [x for x in path.parent.rglob("*") if x.name != "__pycache__"]
    # If we have a pyodide build dist folder with wheels in, copy those over
    # and install the wheels in pyodide so we can import this package for tests
    dist_path = Path.cwd() / "dist"
    if dist_path.exists():
        copy_files.extend(list(dist_path.glob("*.whl")))

    copy_files_with_destinations = []
    for src in copy_files:
        dest = Path("test_files") / src.relative_to(Path.cwd())
        copy_files_with_destinations.append((src, dest))

    copy_files_to_emscripten_fs(
        copy_files_with_destinations, selenium, install_wheels=True
    )


def run_in_pyodide_runtest_call(item):
    selenium = item._request.getfixturevalue("selenium")
    item.path.relative_to(Path.cwd())
    copy_files(selenium, item.path)

    def runtest():
        run_test_in_pyodide(item.nodeid, selenium)

    item.runtest = runtest


def run_test_in_pyodide(node_tree_id, selenium, ignore_fail=False):
    """This runs a single test (identified by node_tree_id) inside
    the pyodide runtime. How it does it is by calling pytest on the
    browser pyodide with the full node ID, which is the same
    as it is locally except for the test_files folder base.

    It also has a little bit of cunning which reformats the output
    from the pyodide call to pytest, so that test failures should look
    roughly the same as they would when you are running pytest locally.
    """
    all_args = [
        node_tree_id.removesuffix(f"[{selenium.browser}]").replace(
            f"[{selenium.browser}-", "["
        ),
        "--color=yes",
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
    selenium.clean_logs()
    # get the error from junitxml
    root = ET.fromstring(ret_xml)
    fails = root.findall("*/testcase[failure]")
    for fail in fails:
        failure = fail.find("failure")
        if failure is not None and failure.text:
            fail_txt = failure.text
        else:
            fail_txt = ""
        if not ignore_fail:
            pytest.fail(fail_txt, pytrace=False)
        return False
    return True
