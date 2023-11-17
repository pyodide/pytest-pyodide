"""
This file is listed in the options.entry_points section of config.cfg so pytest
will look in here for hooks to execute.
"""

import re
from argparse import BooleanOptionalAction
from pathlib import Path
from typing import Any

import pytest
from pytest import Collector, Session

from .run_tests_inside_pyodide import (
    run_in_pyodide_generate_tests,
    run_in_pyodide_runtest_call,
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
        pytest.pyodide_options_stack.append(  # type:ignore[attr-defined]
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


def pytest_pycollect_makemodule(module_path: Path, parent: Collector) -> None:
    from .decorator import record_module_ast

    record_module_ast(module_path)
    # orig_pytest_pycollect_makemodule(module_path, parent)


def pytest_generate_tests(metafunc: Any) -> None:
    if metafunc.config.option.run_in_pyodide:
        run_in_pyodide_generate_tests(metafunc)


def _has_standalone_fixture(item):
    for fixture in item.fixturenames:
        if fixture.startswith("selenium") and "standalone" in fixture:
            return True

    return False


def pytest_collection_modifyitems(items: list[Any]) -> None:
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
    if not item.config.option.run_in_pyodide:
        maybe_skip_item(item)


def maybe_skip_item(item):
    if not hasattr(item, "fixturenames"):
        # Some items like DoctestItem have no fixture
        return

    if item.config.option.run_in_pyodide:
        if "runtime" in item.fixturenames:
            pytest.skip(reason="pyodide specific test, can't run in pyodide")
        return

    if not pytest.pyodide_runtimes and "runtime" in item.fixturenames:
        pytest.skip(reason="Non-host test")
    elif not pytest.pyodide_run_host_test and "runtime" not in item.fixturenames:
        pytest.skip("Host test")


def xfail_browsers_marker_impl(item):
    browser = None
    for fixture in item.fixturenames:
        if fixture.startswith("selenium"):
            browser = item.funcargs[fixture]
            break

    if not browser:
        return

    xfail_msg = parse_xfail_browsers(item).get(browser.browser, None)
    if xfail_msg is not None:
        pytest.xfail(xfail_msg)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item):
    if item.config.option.run_in_pyodide:
        run_in_pyodide_runtest_call(item)
    else:
        xfail_browsers_marker_impl(item)
