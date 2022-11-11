import ast
import pickle
import sys
from base64 import b64decode, b64encode
from collections.abc import Callable, Collection
from copy import deepcopy
from io import BytesIO
from typing import Any, Protocol

import pytest

from .hook import ORIGINAL_MODULE_ASTS, REWRITTEN_MODULE_ASTS
from .pyodide import JsException
from .utils import package_is_built as _package_is_built


def package_is_built(package_name: str):
    return _package_is_built(package_name, pytest.pyodide_dist_dir)  # type: ignore[arg-type]


class SeleniumType(Protocol):
    JavascriptException: type
    browser: str

    def load_package(self, pkgs: str | list[str]):
        ...

    def run_async(self, code: str):
        ...

    def run_js(self, code: str):
        ...


class _ReadableFileobj(Protocol):
    def read(self, __n: int) -> bytes:
        ...

    def readline(self) -> bytes:
        ...


class Unpickler(pickle.Unpickler):
    def __init__(self, file: _ReadableFileobj, selenium: SeleniumType):
        super().__init__(file)
        self.selenium = selenium

    def persistent_load(self, pid: Any) -> Any:
        if not isinstance(pid, tuple) or len(pid) != 2 or pid[0] != "PyodideHandle":
            raise pickle.UnpicklingError("unsupported persistent object")
        ptr = pid[1]
        # the PyodideHandle needs access to selenium in order to free the
        # reference count.
        return PyodideHandle(self.selenium, ptr)

    def find_class(self, module: str, name: str) -> Any:
        """
        Catch exceptions that only exist in the pyodide environment and
        convert them to exception in the host.
        """
        if module == "pyodide" and name == "JsException":
            return JsException
        else:
            return super().find_class(module, name)


class Pickler(pickle.Pickler):
    def persistent_id(self, obj: Any) -> Any:
        if not isinstance(obj, PyodideHandle):
            return None
        return ("PyodideHandle", obj.ptr)


class PyodideHandle:
    """This class allows passing a handle for a Pyodide object back to the host.

    On the host side, the handle is an opaque pointer (well we can access the
    pointer but it isn't very useful). When handed back as the argument to
    another run_in_pyodide function, it gets unpickled as the actual object.

    It's unpickled with persistent_load which injects the selenium instance.
    Because of this, we don't bother implementing __setstate__.
    """

    def __init__(self, selenium: SeleniumType, ptr: int):
        self.selenium = selenium
        self.ptr: int | None = ptr

    def __del__(self):
        if self.ptr is None:
            return
        ptr = self.ptr
        self.ptr = None
        self.selenium.run_js(
            f"""
            pyodide._module._Py_DecRef({ptr});
            """
        )


def _encode(obj: Any) -> str:
    """
    Pickle and base 64 encode obj so we can send it to Pyodide using string
    templating.
    """
    b = BytesIO()
    Pickler(b).dump(obj)
    return b64encode(b.getvalue()).decode()


def _decode(result: str, selenium: SeleniumType) -> Any:
    try:
        return Unpickler(BytesIO(b64decode(result)), selenium).load()
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"There was a problem with unpickling the return value/exception from your pyodide environment. "
            f"This usually means the type of the return value does not exist in your host environment. "
            f"The original message is: {exc}. "
        ) from None


def _create_outer_test_function(
    run_test: Callable,
    node: Any,
) -> Callable:
    """
    Create the top level item: it will be called by pytest and it calls
    run_test.

    If the original function looked like:

        @outer_decorators
        @run_in_pyodide
        @inner_decorators
        <async?> def func(<selenium_arg_name>, arg1, arg2, arg3):
            # do stuff

    This wrapper looks like:

        def <func_name>(<selenium_arg_name>, arg1, arg2, arg3):
            run_test(<selenium_arg_name>, (arg1, arg2, arg3))

    Any inner_decorators get ignored. Any outer_decorators get applied by
    the Python interpreter via the normal mechanism
    """
    node_args = deepcopy(node.args)
    if not node_args.args:
        raise ValueError(
            f"Function {node.name} should take at least one argument whose name should start with 'selenium'"
        )

    selenium_arg_name = node_args.args[0].arg
    if not selenium_arg_name.startswith("selenium"):
        raise ValueError(
            f"Function {node.name}'s first argument name '{selenium_arg_name}' should start with 'selenium'"
        )

    new_node = ast.FunctionDef(
        name=node.name, args=node_args, body=[], lineno=1, decorator_list=[]
    )

    run_test_id = "run-test-not-valid-identifier"

    # Make onwards call with two args:
    # 1. <selenium_arg_name>
    # 2. all other arguments in a tuple
    func_body = ast.parse(
        """\
        __tracebackhide__ = True; \
        return run_test(selenium_arg_name, (arg1, arg2, ...)) \
        """.strip()
    ).body
    onwards_call = func_body[1].value  # type: ignore[attr-defined]
    onwards_call.func = ast.Name(id=run_test_id, ctx=ast.Load())
    onwards_call.args[0].id = selenium_arg_name  # Set variable name
    onwards_call.args[1].elts = [  # Set tuple elements
        ast.Name(id=arg.arg, ctx=ast.Load()) for arg in node_args.args[1:]
    ]

    # Add extra <selenium_arg_name> argument
    new_node.body = func_body

    # Make a best effort to show something that isn't total nonsense in the
    # traceback for the generated function when there is an error.
    # This will show:
    # >   run_test(selenium_arg_name, (arg1, arg2, ...))
    # in the traceback.
    def fake_body_for_traceback(arg1, arg2, selenium_arg_name):
        run_test(selenium_arg_name, (arg1, arg2, ...))

    # Adjust line numbers to point into our fake function
    lineno = fake_body_for_traceback.__code__.co_firstlineno
    new_node.end_lineno = 2
    ast.increment_lineno(new_node, lineno)

    mod = ast.Module([new_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    co = compile(mod, __file__, "exec")

    # Need to give our code access to the actual "run_test" object which it
    # invokes.
    globs = {run_test_id: run_test}
    exec(co, globs)

    return globs[node.name]


def initialize_decorator(selenium):
    from pathlib import Path

    _decorator_in_pyodide = (
        Path(__file__).parent / "_decorator_in_pyodide.py"
    ).read_text()
    selenium.run(
        f"""
def temp():
    _decorator_in_pyodide = '''{_decorator_in_pyodide}'''
    from importlib.machinery import ModuleSpec
    from importlib.util import module_from_spec

    pkgname = "pytest_pyodide"
    modname = "pytest_pyodide.decorator"
    spec = ModuleSpec(pkgname, None)
    pkg = module_from_spec(spec)
    spec = ModuleSpec(modname, None)
    mod = module_from_spec(spec)

    exec(_decorator_in_pyodide, mod.__dict__)

    import sys

    sys.modules[pkgname] = pkg
    sys.modules[modname] = mod
temp()
del temp
        """
    )


class run_in_pyodide:
    def __new__(cls, function: Callable | None = None, /, **kwargs):
        if function:
            # Probably we were used like:
            #
            # @run_in_pyodide
            # def f():
            #   pass
            return run_in_pyodide(**kwargs)(function)
        else:
            # Just do normal __new__ behavior
            return object.__new__(cls)

    def __init__(
        self,
        packages: Collection[str] = (),
        pytest_assert_rewrites: bool = True,
        *,
        _force_assert_rewrites: bool = False,
    ):
        """
        This decorator can be called in two ways --- with arguments and without
        arguments. If it is called without arguments, then the `function` argument
        catches the function the decorator is applied to. Otherwise, standalone and
        packages are the actual arguments to the decorator.

        See docs/testing.md for details on how to use this.

        Parameters
        ----------
        packages : List[str]
            List of packages to load before running the test

        pytest_assert_rewrites : bool, default = True
            If True, use pytest assertion rewrites. This gives better error messages
            when an assertion fails, but requires us to load pytest.
        """

        self._pkgs = list(packages)
        self._pytest_not_built = False
        if (
            pytest_assert_rewrites
            and not package_is_built("pytest")
            and not _force_assert_rewrites
        ):
            pytest_assert_rewrites = False
            self._pytest_not_built = True

        if pytest_assert_rewrites:
            self._pkgs.append("pytest")

        self._module_asts_dict = (
            REWRITTEN_MODULE_ASTS if pytest_assert_rewrites else ORIGINAL_MODULE_ASTS
        )

        if package_is_built("tblib"):
            self._pkgs.append("tblib")

        self._pytest_assert_rewrites = pytest_assert_rewrites

    def _code_template(self, args: tuple) -> str:
        """
        Unpickle function ast and its arguments, compile and call function, and
        if the function is async await the result. Last, if there was an
        exception, pickle it and send it back.
        """
        return f"""
        async def __tmp():
            __tracebackhide__ = True

            from pytest_pyodide.decorator import run_in_pyodide_main
            return run_in_pyodide_main(
                {_encode(self._mod)!r},
                {_encode(args)!r},
                {self._module_filename!r},
                {self._func_name!r},
                {self._async_func!r},
            )

        try:
            result = await __tmp()
        finally:
            del __tmp
        result
        """

    def _run_test(self, selenium: SeleniumType, args: tuple):
        """The main test runner, called from the AST generated in
        _create_outer_test_function."""
        __tracebackhide__ = True
        code = self._code_template(args)
        if self._pkgs:
            selenium.load_package(self._pkgs)

        r = selenium.run_async(code)
        [status, result] = r

        result = _decode(result, selenium)
        if status:
            raise result
        else:
            return result

    def _generate_pyodide_ast(
        self, module_ast: ast.Module, funcname: str, func_line_no: int
    ) -> None:
        """Generates appropriate AST for the test to run in Pyodide.

        The test ast includes mypy magic imports and the test function definition.
        This will be pickled and sent to Pyodide.
        """
        nodes: list[ast.stmt] = []
        it = iter(module_ast.body)
        while True:
            try:
                node = next(it)
            except StopIteration:
                raise Exception(
                    f"Didn't find function {funcname} (line {func_line_no}) in module."
                ) from None
            # We need to include the magic imports that pytest inserts
            if (
                isinstance(node, ast.Import)
                and node.names[0].asname
                and node.names[0].asname.startswith("@")
            ):
                nodes.append(node)

            if (
                node.end_lineno
                and node.end_lineno > func_line_no
                and node.lineno < func_line_no
            ):
                it = iter(node.body)  # type: ignore[attr-defined]
                continue

            # We also want the function definition for the current test
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if node.lineno < func_line_no:
                continue

            if node.name != funcname:
                raise RuntimeError(
                    f"Internal run_in_pyodide error: looking for function '{funcname}' but found '{node.name}'"
                )

            self._async_func = isinstance(node, ast.AsyncFunctionDef)
            node.decorator_list = []
            nodes.append(node)
            break

        self._mod = ast.Module(nodes, type_ignores=[])
        ast.fix_missing_locations(self._mod)

        self._node = node

    def __call__(self, f: Callable) -> Callable:
        func_name = f.__name__
        module_filename = sys.modules[f.__module__].__file__ or ""
        module_ast = self._module_asts_dict[module_filename]

        func_line_no = f.__code__.co_firstlineno

        # _code_template needs this info.
        self._generate_pyodide_ast(module_ast, func_name, func_line_no)
        self._func_name = func_name
        self._module_filename = module_filename

        wrapper = _create_outer_test_function(self._run_test, self._node)

        return wrapper
