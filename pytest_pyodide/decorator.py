import ast
import functools
import pickle
import sys
from base64 import b64decode, b64encode
from collections.abc import Callable, Collection
from copy import deepcopy
from io import BytesIO
from typing import Any, Protocol

import pytest

from .copy_files_to_pyodide import copy_files_to_emscripten_fs
from .hook import ORIGINAL_MODULE_ASTS, REWRITTEN_MODULE_ASTS
from .runner import _BrowserBaseRunner
from .utils import package_is_built as _package_is_built

MaybeAsyncFuncDef = ast.FunctionDef | ast.AsyncFunctionDef


def package_is_built(package_name: str):
    return _package_is_built(package_name, pytest.pyodide_dist_dir)


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
            f"The original message is: {exc}."
        ) from None


def all_args(funcdef: MaybeAsyncFuncDef) -> list[ast.arg]:
    vararg = [funcdef.args.vararg] if funcdef.args.vararg else []
    kwarg = [funcdef.args.kwarg] if funcdef.args.kwarg else []
    return (
        funcdef.args.posonlyargs
        + funcdef.args.args
        + vararg
        + funcdef.args.kwonlyargs
        + kwarg
    )


def prepare_inner_funcdef(funcdef: MaybeAsyncFuncDef) -> MaybeAsyncFuncDef:
    funcdef = deepcopy(funcdef)
    funcdef.decorator_list = []
    # Delete all type annotations
    for arg in all_args(funcdef):
        arg.annotation = None
    funcdef.returns = None
    args = funcdef.args
    args.args = all_args(funcdef)
    args.defaults = []
    args.posonlyargs = []
    args.kwonlyargs = []
    args.vararg = None
    args.kwarg = None
    funcdef.args.kw_defaults = []
    return funcdef


def value_to_name(globs: dict[str, Any], value: Any) -> ast.Name:
    """We can't put values in an `ast.Const` node unless they are deeply
    immutable (they must be of type int, float, complex, bool, string, bytes, or
    a tuple or frozenset whose entries are deeply immutable).

    So put the actual values into a dict with a unique id and return a `Name`
    node that loads the values.
    """
    index = f"v-{len(globs)}"
    globs[index] = value
    return ast.Name(index, ast.Load())


def value_to_name_or_none(
    globs: dict[str, Any], d: dict[str, Any], k: str
) -> ast.Name | None:
    if k not in d:
        return None
    return value_to_name(globs, d[k])


def prepare_outer_funcdef(
    funcdef: MaybeAsyncFuncDef, f: Callable
) -> tuple[MaybeAsyncFuncDef, dict[str, Any]]:
    funcdef = deepcopy(funcdef)
    # Clear out the decorator list.
    funcdef.decorator_list = []
    # Pull the default and annotation values off of the original function
    # object. In case they refer to local variables this gets the values from
    # the scope in which the function was originally defined. We use
    # value_to_name to stick the actual value into globs and put make a `Name`
    # node to load them out of globs.
    globs: dict[str, Any] = {}
    defaults: tuple[Any, ...] = f.__defaults__ or ()
    kwdefaults = f.__kwdefaults__ or {}
    for arg in all_args(funcdef):
        arg.annotation = value_to_name_or_none(globs, f.__annotations__, arg.arg)
    funcdef.returns = value_to_name_or_none(globs, f.__annotations__, "return")
    funcdef.args.defaults = [value_to_name(globs, x) for x in defaults]
    funcdef.args.kw_defaults = [
        value_to_name_or_none(globs, kwdefaults, arg.arg)
        for arg in funcdef.args.kwonlyargs
    ]

    return funcdef, globs


def _create_outer_func(
    run: Callable, funcdef: MaybeAsyncFuncDef, f: Callable
) -> Callable:
    """
    Create the top level item: it will be called by pytest and it calls
    run.

    If the original function looked like:

        @outer_decorators
        @run_in_pyodide
        @inner_decorators
        <async?> def func(<selenium_arg_name>, arg1, arg2, arg3):
            # do stuff

    This wrapper looks like:

        def <func_name>(<selenium_arg_name>, arg1, arg2, arg3):
            run(<selenium_arg_name>, (arg1, arg2, arg3))

    Any inner_decorators get ignored. Any outer_decorators get applied by
    the Python interpreter via the normal mechanism
    """
    funcdef, globs = prepare_outer_funcdef(funcdef, f)

    args = all_args(funcdef)
    if not args:
        raise ValueError(
            f"Function {funcdef.name} should take at least one argument whose name should start with 'selenium'"
        )

    selenium_arg_name = args[0].arg
    if not selenium_arg_name.startswith("selenium"):
        raise ValueError(
            f"Function {funcdef.name}'s first argument name '{selenium_arg_name}' should start with 'selenium'"
        )

    funcdef = ast.FunctionDef(
        name=funcdef.name,
        args=funcdef.args,
        returns=funcdef.returns,
        body=[],
        lineno=1,
        decorator_list=[],
    )

    run_id = "run-not-valid-identifier"

    # Make onwards call with two args:
    # 1. <selenium_arg_name>
    # 2. all other arguments in a tuple
    func_body = ast.parse(
        """\
        __tracebackhide__ = True; \
        return run(selenium_arg_name, (arg1, arg2, ...)) \
        """.strip()
    ).body
    onwards_call = func_body[1].value  # type: ignore[attr-defined]
    onwards_call.func = ast.Name(id=run_id, ctx=ast.Load())
    onwards_call.args[0].id = selenium_arg_name  # Set variable name
    onwards_call.args[1].elts = [  # Set tuple elements
        ast.Name(id=arg.arg, ctx=ast.Load()) for arg in args[1:]
    ]

    # Add extra <selenium_arg_name> argument
    funcdef.body = func_body
    funcdef.end_lineno = 2

    # Make a best effort to show something that isn't total nonsense in the
    # traceback for the generated function when there is an error.
    # This will show:
    # >   run(selenium_arg_name, (arg1, arg2, ...))
    # in the traceback.
    def fake_body_for_traceback(arg1, arg2, selenium_arg_name):
        run(selenium_arg_name, (arg1, arg2, ...))

    # Adjust line numbers to point into our fake function
    lineno = fake_body_for_traceback.__code__.co_firstlineno
    ast.increment_lineno(funcdef, lineno)

    mod = ast.Module([funcdef], type_ignores=[])
    ast.fix_missing_locations(mod)
    co = compile(mod, __file__, "exec")

    # Need to give our code access to the actual "run" object which it
    # invokes.
    globs.update({run_id: run})
    exec(co, globs)

    return globs[funcdef.name]


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


def _locate_funcdef(
    module_ast: ast.Module, f: Callable
) -> tuple[list[ast.stmt], MaybeAsyncFuncDef]:
    """Locate the statements from the original module that we need to make our
    wrapper function.

    Returns a pair:
        statements: a list of mypy magic imports that are used for mypy assertion rewrites
        funcdef: The funcdef node that makes our function
    """
    funcname = f.__name__
    func_line_no = f.__code__.co_firstlineno
    statements: list[ast.stmt] = []
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
            statements.append(node)

        if (
            node.end_lineno
            and node.end_lineno > func_line_no
            and node.lineno < func_line_no
        ):
            it = iter(node.body)  # type: ignore[attr-defined]
            continue

        # We also want the function definition node
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue

        if node.lineno < func_line_no:
            continue

        if node.name != funcname:
            raise RuntimeError(
                f"Internal run_in_pyodide error: looking for function '{funcname}' but found '{node.name}'"
            )
        return (statements, node)


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
            List of packages to load before running the function in Pyodide

        pytest_assert_rewrites : bool, default = True
            If True, use pytest assertion rewrites. This gives better error messages
            when an assertion fails, but requires us to load pytest.
        """

        self._pkgs = list(packages)
        pytest_assert_rewrites = _force_assert_rewrites or (
            pytest_assert_rewrites and package_is_built("pytest")
        )

        if pytest_assert_rewrites:
            self._pkgs.append("pytest")

        self._module_asts_dict = (
            REWRITTEN_MODULE_ASTS if pytest_assert_rewrites else ORIGINAL_MODULE_ASTS
        )

        tblib_variants = (
            "pyodide-tblib",
            "tblib",
        )  # https://github.com/ionelmc/python-tblib/pull/66
        for pkg in tblib_variants:
            if package_is_built(pkg):
                self._pkgs.append(pkg)
                break

    def __call__(self, f: Callable) -> Callable:
        module = sys.modules[f.__module__]
        module_filename = module.__file__ or ""
        module_ast = self._module_asts_dict[module_filename]

        statements, funcdef = _locate_funcdef(module_ast, f)
        inner_funcdef = prepare_inner_funcdef(funcdef)
        statements.append(inner_funcdef)
        new_ast_module = ast.Module(statements, type_ignores=[])

        wrapper = _create_outer_func(self._run, funcdef, f)
        functools.update_wrapper(wrapper, f)

        # Store information needed by self._code_template
        self._mod = new_ast_module
        self._module_filename = module_filename
        self._func_name = f.__name__
        self._async_func = isinstance(funcdef, ast.AsyncFunctionDef)
        return wrapper

    def _run(self, selenium: SeleniumType, args: tuple):
        """The main runner, called from the AST generated in _create_outer_func."""
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


def copy_files_to_pyodide(file_list, install_wheels=True, recurse_directories=True):
    """A decorator that copies files across to pyodide"""

    def wrap(fn):
        @functools.wraps(fn)
        def wrapped_f(*args, **argv):
            # get selenium from args
            selenium = None
            for a in args:
                if isinstance(a, _BrowserBaseRunner):
                    selenium = a
            for a in argv.values():
                if isinstance(a, _BrowserBaseRunner):
                    selenium = a
            if not selenium:
                raise RuntimeError(
                    "copy_files_to_pyodide needs a selenium argument to your test fixture"
                )
            copy_files_to_emscripten_fs(
                file_list,
                selenium,
                install_wheels=install_wheels,
                recurse_directories=recurse_directories,
            )
            return fn(*args, **argv)

        return wrapped_f

    return wrap
