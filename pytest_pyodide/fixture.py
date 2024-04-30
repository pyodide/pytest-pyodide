import contextlib
import functools
import inspect
import os
from pathlib import Path
from typing import Any

import pytest

from .runner import (
    CHROME_FLAGS,
    FIREFOX_FLAGS,
    NodeRunner,
    PlaywrightChromeRunner,
    PlaywrightFirefoxRunner,
    SeleniumChromeRunner,
    SeleniumFirefoxRunner,
    SeleniumSafariRunner,
    _BrowserBaseRunner,
)
from .server import spawn_web_server
from .utils import parse_driver_timeout, set_webdriver_script_timeout


@pytest.fixture(scope="module")
def playwright_browsers(request):
    yield from _playwright_browsers(request)


def _playwright_browsers(request):
    if request.config.option.runner.lower() != "playwright":
        yield {}
    else:
        # import playwright here to allow running tests without playwright installation
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.exit(
                "playwright not installed. try `pip install playwright && python -m playwright install`",
                returncode=1,
            )

        runtimes = pytest.pyodide_runtimes

        with sync_playwright() as p:
            browsers: dict[str, Any] = {}
            supported_browsers: dict[str, tuple[str, list[str]]] = {
                # browser name: (attr_name, flags)
                "firefox": ("firefox", FIREFOX_FLAGS),
                "chrome": ("chromium", CHROME_FLAGS),
                # TODO: enable webkit
                # "webkit": (),
            }
            try:
                for runtime in runtimes:
                    if runtime not in supported_browsers:
                        pytest.exit(
                            f"Unsupported runtime for playwright: {runtime}",
                            returncode=1,
                        )

                    attr_name, flags = supported_browsers[runtime]
                    browsers[runtime] = getattr(p, attr_name).launch(args=flags)

            except Exception as e:
                pytest.exit(f"playwright failed to launch\n{e}", returncode=1)
            try:
                yield browsers
            finally:
                for browser in browsers.values():
                    browser.close()


@contextlib.contextmanager
def selenium_common(
    request,
    runtime,
    web_server_main,
    load_pyodide=True,
    script_type="classic",
    browsers=None,
    jspi=False,
):
    """Returns an initialized selenium object.

    If `_should_skip_test` indicate that the test will be skipped,
    return None, as initializing Pyodide for selenium is expensive
    """

    server_hostname, server_port, server_log = web_server_main
    runner_type = request.config.option.runner.lower()

    runner_set: dict[tuple[str, str], type[_BrowserBaseRunner]] = {
        ("selenium", "firefox"): SeleniumFirefoxRunner,
        ("selenium", "chrome"): SeleniumChromeRunner,
        ("selenium", "safari"): SeleniumSafariRunner,
        ("selenium", "node"): NodeRunner,
        ("playwright", "firefox"): PlaywrightFirefoxRunner,
        ("playwright", "chrome"): PlaywrightChromeRunner,
        ("playwright", "node"): NodeRunner,
    }

    runner_cls = runner_set.get((runner_type, runtime))
    if runner_cls is None:
        raise AssertionError(f"Unknown runner or browser: {runner_type} / {runtime}")

    dist_dir = Path(os.getcwd(), request.config.getoption("--dist-dir"))
    runner = runner_cls(
        server_port=server_port,
        server_hostname=server_hostname,
        server_log=server_log,
        load_pyodide=load_pyodide,
        browsers=browsers,
        script_type=script_type,
        dist_dir=dist_dir,
        jspi=jspi,
    )
    try:
        yield runner
    finally:
        runner.quit()


def rename_fixture(orig_name, new_name):
    def use_variant(f):
        sig = inspect.signature(f)
        new_params = []
        for p in sig.parameters.values():
            if p.name == orig_name:
                p = p.replace(name=new_name)
            new_params.append(p)
        new_sig = sig.replace(parameters=new_params)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if new_name in kwargs:
                kwargs[orig_name] = kwargs.pop(new_name)
            return f(*args, **kwargs)

        wrapper.__signature__ = new_sig  # type:ignore[attr-defined]
        return wrapper

    return use_variant


standalone = rename_fixture("selenium", "selenium_standalone")


@pytest.fixture(scope="function")
def selenium_standalone(request, runtime, web_server_main, playwright_browsers):
    with selenium_common(
        request, runtime, web_server_main, browsers=playwright_browsers
    ) as selenium:
        with set_webdriver_script_timeout(
            selenium, script_timeout=parse_driver_timeout(request.node)
        ):
            try:
                yield selenium
            finally:
                print(selenium.logs)


@pytest.fixture(scope="function")
def selenium_standalone_refresh(selenium):
    """
    Experimental standalone fixture which refreshes a page instead of
    instantiating a new webdriver session.
    """
    selenium.clean_logs()

    yield selenium

    selenium.refresh()
    selenium.load_pyodide()
    selenium.initialize_pyodide()
    selenium.save_state()
    selenium.restore_state()


@pytest.fixture(scope="module")
def selenium_esm(request, runtime, web_server_main, playwright_browsers):
    with selenium_common(
        request,
        runtime,
        web_server_main,
        load_pyodide=True,
        browsers=playwright_browsers,
        script_type="module",
    ) as selenium:
        with set_webdriver_script_timeout(
            selenium, script_timeout=parse_driver_timeout(request.node)
        ):
            try:
                yield selenium
            finally:
                print(selenium.logs)


@contextlib.contextmanager
def selenium_standalone_noload_common(
    request, runtime, web_server_main, playwright_browsers, script_type="classic"
):
    with selenium_common(
        request,
        runtime,
        web_server_main,
        load_pyodide=False,
        browsers=playwright_browsers,
        script_type=script_type,
    ) as selenium:
        with set_webdriver_script_timeout(
            selenium, script_timeout=parse_driver_timeout(request.node)
        ):
            try:
                yield selenium
            finally:
                print(selenium.logs)


@pytest.fixture(scope="function")
def selenium_webworker_standalone(
    request, runtime, web_server_main, playwright_browsers, script_type
):
    # Avoid loading the fixture if the test is going to be skipped
    if runtime == "firefox" and script_type == "module":
        pytest.skip("firefox does not support module type web worker")

    if runtime == "node":
        pytest.skip("no support in node")

    with selenium_standalone_noload_common(
        request, runtime, web_server_main, playwright_browsers, script_type=script_type
    ) as selenium:
        yield selenium


@pytest.fixture(scope="function")
def selenium_standalone_noload(request, runtime, web_server_main, playwright_browsers):
    """Only difference between this and selenium_webworker_standalone is that
    this also tests on node."""

    with selenium_standalone_noload_common(
        request, runtime, web_server_main, playwright_browsers
    ) as selenium:
        yield selenium


# selenium instance cached at the module level
@pytest.fixture(scope="module")
def selenium_module_scope(request, runtime, web_server_main, playwright_browsers):
    with selenium_common(
        request, runtime, web_server_main, browsers=playwright_browsers
    ) as selenium:
        yield selenium


# Hypothesis is unhappy with function scope fixtures. Instead, use the
# module scope fixture `selenium_module_scope` and use:
# `with selenium_context_manager(selenium_module_scope) as selenium`
@contextlib.contextmanager
def selenium_context_manager(selenium_module_scope):
    try:
        selenium_module_scope.clean_logs()
        yield selenium_module_scope
    finally:
        try:
            print(selenium_module_scope.logs)
        except ValueError:
            # For reasons I don't entirely understand, it is possible for
            # selenium to be closed before this is executed. In that case, just
            # skip printing the logs and we can exit cleanly.
            pass


@pytest.fixture
def selenium(request, selenium_module_scope):
    with selenium_context_manager(
        selenium_module_scope
    ) as selenium, set_webdriver_script_timeout(
        selenium, script_timeout=parse_driver_timeout(request.node)
    ):
        yield selenium


@pytest.fixture
def selenium_jspi(request, runtime, web_server_main, playwright_browsers):
    yield from selenium_jspi_inner(
        request, runtime, web_server_main, playwright_browsers
    )


def selenium_jspi_inner(request, runtime, web_server_main, playwright_browsers):
    if runtime in ["firefox", "safari"]:
        pytest.skip(f"jspi not supported in {runtime}")
    if request.config.option.runner.lower() == "playwright":
        pytest.skip("jspi not supported with playwright")
    with selenium_common(
        request, runtime, web_server_main, browsers=playwright_browsers, jspi=True
    ) as selenium, set_webdriver_script_timeout(
        selenium, script_timeout=parse_driver_timeout(request.node)
    ):
        yield selenium


@pytest.fixture(params=[False, True])
def selenium_also_with_jspi(
    selenium, request, runtime, web_server_main, playwright_browsers
):
    jspi = request.param
    if not jspi:
        yield selenium
        return
    yield from selenium_jspi_inner(
        request, runtime, web_server_main, playwright_browsers
    )


@pytest.fixture(scope="function")
def console_html_fixture(request, runtime, web_server_main, playwright_browsers):
    if runtime == "node":
        pytest.skip("no support in node")

    with selenium_common(
        request,
        runtime,
        web_server_main,
        load_pyodide=False,
        browsers=playwright_browsers,
    ) as selenium:
        selenium.goto(
            f"http://{selenium.server_hostname}:{selenium.server_port}/console.html"
        )
        selenium.javascript_setup()
        try:
            yield selenium
        finally:
            print(selenium.logs)


@pytest.fixture(scope="session")
def web_server_main(request):
    """Web server that serves files in the dist directory"""
    with spawn_web_server(request.config.option.dist_dir) as output:
        yield output


@pytest.fixture(scope="session")
def web_server_secondary(request):
    """Secondary web server that serves files dist directory"""
    with spawn_web_server(request.config.option.dist_dir) as output:
        yield output


@pytest.fixture(params=["classic", "module"], scope="module")
def script_type(request):
    return request.param
