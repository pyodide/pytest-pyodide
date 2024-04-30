"""
This file is listed in the options.entry_points section of config.cfg so pytest
will look in here for hooks to execute.
"""

import ast
import re
import sys
from argparse import BooleanOptionalAction
from copy import copy, deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook, rewrite_asserts
from _pytest.python import (
    pytest_pycollect_makemodule as orig_pytest_pycollect_makemodule,
)
from pytest import Collector, Session

from .copy_files_to_pyodide import copy_files_to_emscripten_fs
from .run_tests_inside_pyodide import (
    close_pyodide_browsers,
    get_browser_pyodide,
    run_test_in_pyodide,
)
from .utils import parse_xfail_browsers

RUNTIMES = ["firefox", "chrome", "safari", "node"]
RUNTIMES_AND_HOST = RUNTIMES + ["host"]
RUNTIMES_NO_HOST = [f"{runtime}-no-host" for runtime in RUNTIMES]


def _filter_runtimes(runtime: str) -> tuple[bool, set[str]]:
    """Preprocess the given runtime commandline parameter

    >>> _filter_runtimes("chrome")
    (True, {'chrome'})
    >>> _filter_runtimes("chrome-no-host")
    (False, {'chrome'})
    >>> _filter_runtimes("chrome-no-host, host, firefox")
    (True, ...)
    """

    # Always run host test, unless 'no-host' is given.
    run_host = True

    # "chrome, firefox, node" ==> ["chrome", "firefox", "node"]
    runtimes = [rt.strip() for rt in runtime.split(",")]

    # remove duplicates
    runtime_set = set(runtimes)

    runtime_filtered = set()
    for rt in runtime_set:
        if rt.endswith("-no-host"):
            run_host = False
            rt = rt.replace("-no-host", "")

        runtime_filtered.add(rt)

    # If '--rt "chrome-no-host, host"' is given, we run host tests.
    run_host = run_host or ("host" in runtime_filtered)

    runtime_filtered.discard("host")

    for rt in runtime_filtered:
        if rt not in RUNTIMES:
            raise ValueError(f"Invalid runtime: {rt}")

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

    config.option.dist_dir = Path(config.option.dist_dir).resolve()
    run_host, runtimes = _filter_runtimes(config.option.runtime)

    if not hasattr(pytest, "pyodide_options_stack"):
        pytest.pyodide_options_stack = []
    else:
        pytest.pyodide_options_stack.append(
            [
                pytest.pyodide_run_host_test,
                pytest.pyodide_runtimes,
                pytest.pyodide_dist_dir,
            ]
        )
    pytest.pyodide_run_host_test = run_host
    pytest.pyodide_runtimes = runtimes
    pytest.pyodide_dist_dir = config.option.dist_dir


def pytest_unconfigure(config):
    close_pyodide_browsers()
    try:
        (
            pytest.pyodide_run_host_test,
            pytest.pyodide_runtimes,
            pytest.pyodide_dist_dir,
        ) = pytest.pyodide_options_stack.pop()  # type:ignore[attr-defined]
    except IndexError:
        pass


@pytest.hookimpl(tryfirst=True)
def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption(
        "--dist-dir",
        dest="dist_dir",
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
        "--run-in-pyodide",
        action=BooleanOptionalAction,
        help="Run standard pytest tests, but in pyodide",
    )

    group.addoption(
        "--rt",
        "--runtime",
        dest="runtime",
        default="node",
        help="Select runtimes to run tests (default: %(default)s)",
    )


# We don't know the params yet, but we can set them when we do know them in
# pytest_collection
@pytest.fixture(params=[], scope="module")
def runtime(request):
    return request.param


def set_runtime_fixture_params(session):
    rt = session._fixturemanager._arg2fixturedefs["runtime"]
    rt[0].params = pytest.pyodide_runtimes


def pytest_collection(session: Session):
    from .doctest import patch_doctest_runner

    patch_doctest_runner()
    session.config.option.doctestmodules_ = session.config.option.doctestmodules
    set_runtime_fixture_params(session)


def pytest_collect_file(file_path: Path, parent: Collector):
    # Have to set doctestmodules to False to prevent original hook from
    # triggering
    parent.config.option.doctestmodules = False
    doctestmodules = getattr(parent.config.option, "doctestmodules_", False)
    from .doctest import collect_doctests

    # Call our collection hook instead. (If there are no doctests to collect,
    # collect_doctests will return None)
    return collect_doctests(file_path, parent, doctestmodules)


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


def pytest_pycollect_makemodule(module_path: Path, parent: Collector) -> None:
    source = module_path.read_bytes()
    strfn = str(module_path)
    tree = ast.parse(source, filename=strfn)
    ORIGINAL_MODULE_ASTS[strfn] = tree
    tree2 = deepcopy(tree)
    rewrite_asserts(tree2, source, strfn, REWRITE_CONFIG)
    REWRITTEN_MODULE_ASTS[strfn] = tree2
    orig_pytest_pycollect_makemodule(module_path, parent)


STANDALONE_FIXTURES = [
    "selenium_standalone",
    "selenium_standalone_noload",
    "selenium_webworker_standalone",
]


def _has_standalone_fixture(item):
    for fixture in item._request.fixturenames:
        if fixture in STANDALONE_FIXTURES:
            return True

    return False


def modifyitems_run_in_pyodide(items: list[Any]):
    # TODO: get rid of this
    # if we are running tests in pyodide, then run all tests for each runtime
    new_items = []
    # if pyodide_runtimes is not a singleton this is buggy...
    # pytest_collection_modifyitems is only allowed to filter and reorder items,
    # not to add new ones...
    for runtime in pytest.pyodide_runtimes:  # type: ignore[attr-defined]
        if runtime == "host":
            continue
        for x in items:
            x = copy(x)
            x.pyodide_runtime = runtime
            new_items.append(x)
    items[:] = new_items
    return


def pytest_collection_modifyitems(items: list[Any]) -> None:
    # TODO: is this the best way to figure out if run_in_pyodide was requested?
    if items and items[0].config.option.run_in_pyodide:
        modifyitems_run_in_pyodide(items)

    # Run all Safari standalone tests first
    # Since Safari doesn't support more than one simultaneous session, we run all
    # selenium_standalone Safari tests first. We preserve the order of other
    # tests.
    OFFSET = 10000
    counter = [0]

    def _get_item_position(item):
        counter[0] += 1
        if any(
            [re.match(r"^safari[\-$]?", el) for el in item.keywords._markers.keys()]
        ) and _has_standalone_fixture(item):
            return counter[0] - OFFSET
        return counter[0]

    items[:] = sorted(items, key=_get_item_position)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if item.config.option.run_in_pyodide:
        if not hasattr(item, "fixturenames"):
            return
        if pytest.pyodide_runtimes and "runtime" in item.fixturenames:
            pytest.skip(reason="pyodide specific test, can't run in pyodide")
        else:
            # Pass this test to pyodide runner
            # First: make sure that pyodide has the test folder copied over
            item_path = Path(item.path)
            copy_files = list(item_path.parent.rglob("*"))
            # If we have a pyodide build dist folder with wheels in, copy those over
            # and install the wheels in pyodide so we can import this package for tests
            dist_path = Path.cwd() / "dist"
            if dist_path.exists():
                copy_files.extend(list(dist_path.glob("*.whl")))

            copy_files_with_destinations = []
            for src in copy_files:
                dest = Path("test_files") / src.relative_to(Path.cwd())
                copy_files_with_destinations.append((src, dest))

            class RequestType:
                config = item.config
                node = item

            selenium = get_browser_pyodide(
                request=cast(pytest.FixtureRequest, RequestType),
                runtime=item.pyodide_runtime,
            )
            copy_files_to_emscripten_fs(
                copy_files_with_destinations, selenium, install_wheels=True
            )
    else:
        if not hasattr(item, "fixturenames"):
            # Some items like DoctestItem have no fixture
            return
        if not pytest.pyodide_runtimes and "runtime" in item.fixturenames:
            pytest.skip(reason="Non-host test")
        elif not pytest.pyodide_run_host_test and "runtime" not in item.fixturenames:
            pytest.skip("Host test")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if item.config.option.run_in_pyodide:

        def _run_in_pyodide(self):
            class RequestType:
                config = item.config
                node = item

            selenium = get_browser_pyodide(
                request=cast(pytest.FixtureRequest, RequestType),
                runtime=item.pyodide_runtime,
            )
            run_test_in_pyodide(self.nodeid, selenium)

        item.runtest = _run_in_pyodide.__get__(item, item.__class__)
        yield
        return

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
