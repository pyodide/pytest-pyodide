import ast
from collections.abc import Callable
from copy import copy
from doctest import DocTest, DocTestRunner, register_optionflag
from pathlib import Path
from typing import cast

import pytest
from _pytest.doctest import (
    DoctestModule,
    DoctestTextfile,
    _is_doctest,
    _is_main_py,
    _is_setup_py,
)
from _pytest.python import CallSpec2
from _pytest.scope import Scope
from pytest import Collector

from . import run_in_pyodide
from .hook import ORIGINAL_MODULE_ASTS

__all__ = ["patch_doctest_runner", "collect_doctests"]


# Record the ast of this file so we can use run_in_pyodide in here
# TODO: maybe extract this as a utility function for clarity?
ORIGINAL_MODULE_ASTS[__file__] = ast.parse(
    Path(__file__).read_bytes(), filename=__file__
)
# make doctest aware of our `doctest: +RUN_IN_PYODIDE`` optionflag
RUN_IN_PYODIDE = register_optionflag("RUN_IN_PYODIDE")


def runtime_parametrize(item):
    """Force test item to be parametrized over runtimes.

    Unfortunately we have to do this manually since pytest_generate_tests only
    runs on Python tests.
    """
    scope = Scope.from_user("module", "")
    name: str
    runtimes = cast(list[str], pytest.pyodide_runtimes)
    for idx, name in enumerate(runtimes):
        newitem = copy(item)
        # dtest is the actual doctest, we have to mutate it to allow pickling so
        # better copy it too.
        newitem.dtest = copy(item.dtest)
        # Add e.g., `[chrome]` to the name, have to add it to the nodeid too or
        # else it won't be displayed on the terminal.
        newitem.name += f"[{name}]"
        newitem._nodeid += f"[{name}]"
        # Add runtime fixture to the list of fixtures and give it a specific
        # value. Normally this would be done by metafunc.parametrize but it is
        # hard to get access to that from here.
        newitem.fixturenames = ("runtime",)
        newitem.callspec = CallSpec2(
            params={"runtime": name},
            indices={"runtime": idx},
            _idlist=[name],
            _arg2scope={"runtime": scope},
        )
        yield newitem


class PyodideDoctestMixin:
    def collect(self):
        """Call super and then if test includes the RUN_IN_PYODIDE option on the
        first line, make one copy for each Pyodide runtime environment
        """
        for item in super().collect():  # type:ignore[misc]
            pyodide_test = RUN_IN_PYODIDE in item.dtest.examples[0].options
            item.dtest.pyodide_test = pyodide_test
            if not pyodide_test:
                if pytest.pyodide_run_host_test:
                    yield item
                continue
            yield from runtime_parametrize(item)


class PyodideDoctestModule(PyodideDoctestMixin, DoctestModule):
    pass


class PyodideDoctestTextfile(PyodideDoctestMixin, DoctestTextfile):
    pass


def collect_doctests(
    file_path: Path, parent: Collector, doctestmodules: bool
) -> PyodideDoctestModule | PyodideDoctestTextfile | None:
    """This is similar to _pytest.doctest.pytest_collect_file but it uses
    PyodideDoctestModule and PyodideDoctestTextfile which may run tests in
    Pyodide.
    """
    if (
        doctestmodules
        and file_path.suffix == ".py"
        and not any((_is_setup_py(file_path), _is_main_py(file_path)))
    ):
        return PyodideDoctestModule.from_parent(parent, path=file_path)
    if _is_doctest(parent.config, file_path, parent):
        return PyodideDoctestTextfile.from_parent(parent, path=file_path)
    return None


host_DocTestRunner_run = DocTestRunner.run


def patch_doctest_runner() -> None:
    DocTestRunner.run = run_doctest_in_pyodide_outer  # type: ignore[method-assign]


def run_doctest_in_pyodide_outer(
    self: DocTestRunner,
    test: DocTest,
    compileflags: int | None = None,
    out: Callable[[str], object] | None = None,
    clear_globs: bool = True,
):
    if not test.pyodide_test:  # type:ignore[attr-defined]
        # Run host test as normal
        return host_DocTestRunner_run(self, test, compileflags, out, clear_globs)

    # pytest conveniently inserts getfixture into the test globals. This saves
    # us a lot of effort.
    getfixture = test.globs["getfixture"]
    selenium = getfixture("selenium")

    # Can't pickle test with its globals. We retain the __name__ so that we can
    # figure out how to restore the globals inside of pyodide.
    test.globs = {k: test.globs[k] for k in ["__name__"]}

    # It would be nice if we could pickle DocTestRunner, but pytest has made it
    # very not pickleable. After fixing a few name resolution issues I can get
    # it to pickle successfully but I get some pickle internal error on
    # unpickling.
    #
    # So we just take the DocTestRunner apart and put it back together inside
    # Pyodide.
    optionflags = self.optionflags
    continue_on_failure = self.continue_on_failure  # type:ignore[attr-defined]

    return run_doctest_in_pyodide_inner(
        selenium, optionflags, continue_on_failure, test, compileflags, out, clear_globs
    )


@run_in_pyodide(pytest_assert_rewrites=False, packages=["pytest"])
def run_doctest_in_pyodide_inner(
    selenium,
    optionflags,
    continue_on_failure,
    test,
    compileflags,
    out,
    clear_globs,
):
    # Recreate the DocTestRunner
    #
    # It would reduce the amount of pytest internals we have to touch to
    # pickle the DocTestRunner rather than recreating it but it didn't seem
    # to work.
    from _pytest.doctest import _get_checker, _get_runner

    self = _get_runner(
        verbose=False,
        optionflags=optionflags,
        checker=_get_checker(),
        continue_on_failure=continue_on_failure,
    )

    # Put the appropriate global variables back. We do a lot less than what
    # doctest does here, but we currently don't anything but module globals
    # in our tests.
    from importlib import import_module

    try:
        mod = import_module(test.globs["__name__"])
        test.globs = mod.__dict__.copy()
    except ModuleNotFoundError:
        # Oops the test file isn't in the Pyodide file system.
        # TODO: maybe we shouldn't suppress this error??
        pass
    try:
        return self.run(test, compileflags, out, clear_globs)
    except Exception:
        # Some exceptions carry a reference to the test which cannot be
        # pickled with its global variables. Clear them out to ensure that
        # we can pickle the exception we threw.
        test.globs = {}
        raise
