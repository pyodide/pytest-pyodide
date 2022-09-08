import ast
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook, rewrite_asserts
from _pytest.python import (
    pytest_pycollect_makemodule as orig_pytest_pycollect_makemodule,
)

from .utils import parse_xfail_browsers

RUNTIMES = ["firefox", "chrome", "safari", "node"]
RUNTIMES_AND_HOST = RUNTIMES + ["host"]
RUNTIMES_NO_HOST = [f"{runtime}-no-host" for runtime in RUNTIMES]


def _filter_runtimes(runtime: list[str]) -> tuple[bool, set[str]]:
    # Always run host test, unless 'no-host' is given.
    run_host = True

    # remove duplicates
    runtime_set = set(runtime)

    runtime_filtered = set()
    for rt in runtime_set:
        if rt.endswith("-no-host"):
            run_host = False
            rt = rt.replace("-no-host", "")

        runtime_filtered.add(rt)

    # If '--rt chrome-no-host --rt host' is given, we run host tests.
    run_host = run_host or ("host" in runtime_filtered)

    runtime_filtered.discard("host")

    return run_host, runtime_filtered


def pytest_configure(config):

    config.addinivalue_line(
        "markers",
        "skip_refcount_check: Don't run refcount checks",
    )

    config.addinivalue_line(
        "markers",
        "skip_pyproxy_check: Don't run pyproxy allocation checks",
    )

    config.addinivalue_line(
        "markers",
        "driver_timeout: Set script timeout in WebDriver",
    )

    config.addinivalue_line(
        "markers",
        "xfail_browsers: xfail a test in specific browsers",
    )

    run_host, runtimes = _filter_runtimes(config.option.runtime)
    pytest.pyodide_run_host_test = run_host
    pytest.pyodide_runtimes = runtimes
    pytest.pyodide_dist_dir = config.getoption("--dist-dir")


@pytest.hookimpl(tryfirst=True)
def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption(
        "--dist-dir",
        action="store",
        default="pyodide",
        help="Path to the pyodide dist directory",
        type=Path,
    )
    group.addoption(
        "--runner",
        default="selenium",
        choices=["selenium", "playwright"],
        help="Select testing frameworks, selenium or playwright (default: %(default)s)",
    )
    group.addoption(
        "--rt",
        "--runtime",
        dest="runtime",
        nargs="+",
        default=["node"],
        choices=RUNTIMES_AND_HOST + RUNTIMES_NO_HOST,
        help="Select runtime (default: %(default)s)",
    )


# Handling for pytest assertion rewrites
# First we find the pytest rewrite config. It's an attribute of the pytest
# assertion rewriting meta_path_finder, so we locate that to get the config.


def _get_pytest_rewrite_config() -> Any:
    for meta_path_finder in sys.meta_path:
        if isinstance(meta_path_finder, AssertionRewritingHook):
            break
    else:
        return None
    return meta_path_finder.config


# Now we need to parse the ast of the files, rewrite the ast, and store the
# original and rewritten ast into dictionaries. `run_in_pyodide` will look the
# ast up in the appropriate dictionary depending on whether or not it is using
# pytest assert rewrites.

REWRITE_CONFIG = _get_pytest_rewrite_config()
del _get_pytest_rewrite_config

ORIGINAL_MODULE_ASTS: dict[str, ast.Module] = {}
REWRITTEN_MODULE_ASTS: dict[str, ast.Module] = {}


def pytest_pycollect_makemodule(module_path: Path, path: Any, parent: Any) -> None:
    source = module_path.read_bytes()
    strfn = str(module_path)
    tree = ast.parse(source, filename=strfn)
    ORIGINAL_MODULE_ASTS[strfn] = tree
    tree2 = deepcopy(tree)
    rewrite_asserts(tree2, source, strfn, REWRITE_CONFIG)
    REWRITTEN_MODULE_ASTS[strfn] = tree2
    orig_pytest_pycollect_makemodule(module_path, parent)


def pytest_generate_tests(metafunc: Any) -> None:
    if "runtime" in metafunc.fixturenames:
        metafunc.parametrize("runtime", pytest.pyodide_runtimes, scope="module")


def pytest_collection_modifyitems(items: list[Any]) -> None:
    # Run all Safari standalone tests first
    # Since Safari doesn't support more than one simultaneous session, we run all
    # selenium_standalone Safari tests first. We preserve the order of other
    # tests.

    OFFSET = 10000

    counter = [0]
    standalone_fixtures = [
        "selenium_standalone",
        "selenium_standalone_noload",
        "selenium_webworker_standalone",
    ]

    def _has_standalone_fixture(fixturenames):
        for fixture in fixturenames:
            if fixture in standalone_fixtures:
                return True

        return False

    def _get_item_position(item):
        counter[0] += 1
        if any(
            [re.match(r"^safari[\-$]?", el) for el in item.keywords._markers.keys()]
        ) and _has_standalone_fixture(item._request.fixturenames):
            return counter[0] - OFFSET
        return counter[0]

    items[:] = sorted(items, key=_get_item_position)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if not hasattr(item, "fixturenames"):
        # Some items like DoctestItem has no fixture
        return

    if not pytest.pyodide_runtimes and "runtime" in item.fixturenames:  # type: ignore[truthy-bool]
        pytest.skip(reason="Non-host test")
    elif not pytest.pyodide_run_host_test and "runtime" not in item.fixturenames:  # type: ignore[truthy-bool]
        pytest.skip("Host test")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):

    browser = None
    for fixture in item._fixtureinfo.argnames:
        if fixture.startswith("selenium"):
            browser = item.funcargs[fixture]
            break

    if not browser:
        yield
        return

    xfail_msg = parse_xfail_browsers(item).get(browser.browser, None)
    if xfail_msg is not None:
        pytest.xfail(xfail_msg)

    yield
    return
