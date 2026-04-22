"""
Tests for the ``selenium_worker`` fixture, which drives Pyodide inside a
Web Worker rather than on the main browser thread.

These tests mirror the coverage of the main-thread ``selenium`` fixture
so we know the worker runner behaves the same way end-to-end.
"""

import pytest

from pytest_pyodide import run_in_pyodide
from pytest_pyodide.runner import (
    BrowserWorkerChromeRunner,
    BrowserWorkerFirefoxRunner,
    BrowserWorkerSafariRunner,
    _BrowserWorkerRunnerMixin,
)


# ---------------------------------------------------------------------------
# Host-only tests (no browser required)
# ---------------------------------------------------------------------------


def test_worker_runner_classes_inherit_mixin():
    """Each BrowserWorker* runner must compose the mixin with the matching
    Selenium runner, so it inherits driver setup and worker dispatch."""
    for cls in (
        BrowserWorkerChromeRunner,
        BrowserWorkerFirefoxRunner,
        BrowserWorkerSafariRunner,
    ):
        assert issubclass(cls, _BrowserWorkerRunnerMixin)
        # The mixin's overrides must win over the Selenium base.
        assert cls.run_js_inner is _BrowserWorkerRunnerMixin.run_js_inner
        assert cls.prepare_driver is _BrowserWorkerRunnerMixin.prepare_driver


def test_worker_runner_browser_attributes():
    assert BrowserWorkerChromeRunner.browser == "chrome"
    assert BrowserWorkerFirefoxRunner.browser == "firefox"
    assert BrowserWorkerSafariRunner.browser == "safari"


def test_worker_template_is_served():
    """The worker bootstrap script must be exposed by the dev web server."""
    from pytest_pyodide.server import _default_templates

    tpls = _default_templates()
    assert "/module_webworker_runner.js" in tpls
    body = tpls["/module_webworker_runner.js"].decode()
    # Module worker must pull loadPyodide so ``load_pyodide`` works.
    assert "import { loadPyodide }" in body
    assert "self.loadPyodide = loadPyodide" in body
    # And it must implement the RPC protocol used by the mixin.
    assert "onmessage" in body
    assert "postMessage" in body


# ---------------------------------------------------------------------------
# Worker fixture tests (require a browser)
# ---------------------------------------------------------------------------


def test_selenium_worker_basic(selenium_worker):
    """The fixture must yield an initialized runner with Pyodide loaded
    inside the worker."""
    assert selenium_worker.pyodide_loaded is True


def test_selenium_worker_runs_in_worker_context(selenium_worker):
    """Confirm we're actually executing inside a DedicatedWorkerGlobalScope,
    not on the page's Window."""
    ctor_name = selenium_worker.run_js(
        "return self.constructor.name;",
        pyodide_checks=False,
    )
    assert "Worker" in ctor_name or ctor_name == "DedicatedWorkerGlobalScope"
    # There's no DOM in a worker.
    has_document = selenium_worker.run_js(
        "return typeof document !== 'undefined';",
        pyodide_checks=False,
    )
    assert has_document is False


def test_selenium_worker_run_python(selenium_worker):
    """Round-trip a Python expression through the worker."""
    assert selenium_worker.run("1 + 2") == 3
    assert selenium_worker.run("'hello' + ' world'") == "hello world"


def test_selenium_worker_run_python_async(selenium_worker):
    selenium_worker.run_async(
        """
        import asyncio
        await asyncio.sleep(0)
        """
    )


def test_selenium_worker_js_exception(selenium_worker):
    """Errors raised inside the worker must surface as JavascriptException
    on the host."""
    with pytest.raises(selenium_worker.JavascriptException):
        selenium_worker.run_js(
            "throw new Error('boom from worker');",
            pyodide_checks=False,
        )


def test_selenium_worker_python_error_propagates(selenium_worker):
    """``run_js``'s pyodide error check runs inside the worker too."""
    with pytest.raises(selenium_worker.JavascriptException):
        selenium_worker.run("raise RuntimeError('nope')")


def test_selenium_worker_logs(selenium_worker):
    """console.log inside the worker should be captured by the worker's
    ``self.logs`` and exposed via ``runner.logs``."""
    selenium_worker.clean_logs()
    selenium_worker.run_js(
        "console.log('hello from worker');",
        pyodide_checks=False,
    )
    assert "hello from worker" in selenium_worker.logs
    selenium_worker.clean_logs()
    assert "hello from worker" not in selenium_worker.logs


@run_in_pyodide
def test_selenium_worker_run_in_pyodide(selenium_worker):
    """``run_in_pyodide`` should work with the worker fixture just like it
    does with the main-thread fixture."""
    import sys

    assert sys.platform == "emscripten"


@run_in_pyodide
def test_selenium_worker_no_window(selenium_worker):
    """Workers have no ``window`` global (no DOM)."""
    import js

    assert not hasattr(js, "window")
