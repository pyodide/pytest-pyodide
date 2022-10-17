import pytest
from hypothesis import given, settings

from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.hypothesis import any_strategy, std_hypothesis_settings
from pytest_pyodide.pyodide import JsException
from pytest_pyodide.utils import parse_driver_timeout


@run_in_pyodide
def example_func(selenium):
    pass


@run_in_pyodide(_force_assert_rewrites=True)
def test_selenium1(selenium):
    import pytest

    with pytest.raises(AssertionError, match="assert 6 == 7"):
        x = 6
        y = 7
        assert x == y


run_in_pyodide_alias = run_in_pyodide(_force_assert_rewrites=True)


@run_in_pyodide_alias
def test_selenium2(selenium):
    import pytest

    x = 6
    y = 7
    with pytest.raises(AssertionError, match="assert 6 == 7"):
        assert x == y


@run_in_pyodide(_force_assert_rewrites=True)
async def test_selenium3(selenium):
    from asyncio import sleep

    import pytest

    await sleep(0.01)
    x = 6
    await sleep(0.01)
    y = 7
    with pytest.raises(AssertionError, match="assert 6 == 7"):
        assert x == y


def test_inner_function_closure_error(selenium):
    x = 6

    @run_in_pyodide
    def inner_function(selenium):
        assert x == 6
        return 7

    with pytest.raises(NameError, match="'x' is not defined"):
        inner_function(selenium)


def test_inner_function(selenium):
    @run_in_pyodide
    def inner_function(selenium, x):
        assert x == 6
        return 7

    assert inner_function(selenium, 6) == 7


def test_inner_function_js_exception(selenium):
    @run_in_pyodide
    def inner_function(selenium):
        from pyodide.code import run_js

        run_js("throw 'some error'")

    with pytest.raises(
        JsException,
        match="Error: some error",
    ):
        inner_function(selenium)


def test_not_unpickable_return_value(selenium):
    @run_in_pyodide
    async def inner_function(selenium):
        with open("some_module.py", "w") as fp:
            fp.write("class Test: pass\n")

        from some_module import Test

        return Test()

    with pytest.raises(
        ModuleNotFoundError,
        match="There was a problem with unpickling the return.*",
    ):
        inner_function(selenium)


def complicated_decorator(attr_name: str):
    def inner_func(value):
        def dec(func):
            def wrapper(*args, **kwargs):
                wrapper.dec_info.append((attr_name, value))
                return func(*args, **kwargs)

            wrapper.dec_info = getattr(func, "dec_info", [])
            wrapper.__name__ = func.__name__
            return wrapper

        return dec

    return inner_func


d1 = complicated_decorator("testdec1")
d2 = complicated_decorator("testdec2")


@d1("a")
@d2("b")
@d1("c")
@run_in_pyodide
def example_decorator_func(selenium):
    pass


def test_selenium4(selenium_standalone):
    example_decorator_func(selenium_standalone)
    assert example_decorator_func.dec_info[-3:] == [
        ("testdec1", "a"),
        ("testdec2", "b"),
        ("testdec1", "c"),
    ]


def test_local_fail_load_package(selenium_standalone):
    selenium = selenium_standalone

    def _load_package_error(*args, **kwargs):
        raise OSError("STOP!")

    _load_package_original = selenium.load_package
    selenium.load_package = _load_package_error

    exc = None
    try:
        example_func(selenium)
    except OSError:
        exc = pytest.ExceptionInfo.from_current()
    finally:
        selenium.load_package = _load_package_original

    assert exc
    try:
        exc.getrepr()
    except IndexError as e:
        import traceback

        traceback.print_exception(e)
        raise Exception(
            "run_in_pyodide decorator badly messed up the line numbers."
            " This could crash pytest. Printed the traceback to stdout."
        ) from None


@run_in_pyodide
def test_trivial1(selenium):
    x = 7
    assert x == 7


@run_in_pyodide()
def test_trivial2(selenium):
    x = 7
    assert x == 7


@run_in_pyodide(pytest_assert_rewrites=False)
def test_trivial3(selenium):
    x = 7
    assert x == 7


@pytest.mark.parametrize("jinja2", ["jINja2", "Jinja2"])
@run_in_pyodide
def test_parametrize(selenium, jinja2):
    try:
        assert jinja2.lower() == "jinja2"
    except Exception as e:
        print(e)


@pytest.mark.skip(reason="Nope!")
@run_in_pyodide(pytest_assert_rewrites=False)
def test_skip(selenium):
    x = 6
    assert x == 7


@run_in_pyodide
async def test_run_in_pyodide_async(selenium):
    from asyncio import sleep

    x = 6
    await sleep(0.01)
    assert x == 6


@pytest.mark.skip_refcount_check
@pytest.mark.skip_pyproxy_check
@given(obj=any_strategy)
@settings(
    std_hypothesis_settings,
    max_examples=25,
)
@run_in_pyodide
def test_hypothesis(selenium_standalone, obj):
    from pyodide import to_js

    to_js(obj)


run_in_pyodide_inner = run_in_pyodide()
run_in_pyodide_alias2 = pytest.mark.driver_timeout(40)(run_in_pyodide_inner)


@run_in_pyodide_alias2
def test_run_in_pyodide_alias(request):
    assert parse_driver_timeout(request.node) == 40


@run_in_pyodide
def set_handle(selenium, handle, key, value):
    handle.obj[key] = value


@run_in_pyodide
def assert_get_handle(selenium, handle, key, value):
    assert handle.obj[key] == value


@run_in_pyodide
def returns_handle(selenium):
    import __main__

    from pytest_pyodide.decorator import PyodideHandle

    o = {"a": 6}
    __main__.o = o
    handle = PyodideHandle(o)
    return handle


@run_in_pyodide
def check_refcount(selenium, n):
    import sys

    import __main__

    assert sys.getrefcount(__main__.o) == n


def test_selenium_handle(selenium):
    handle = returns_handle(selenium)
    check_refcount(selenium, 4)
    set_handle(selenium, handle, 7, 2)
    set_handle(selenium, handle, "b", 1)
    assert_get_handle(selenium, handle, "a", 6)
    assert_get_handle(selenium, handle, 7, 2)
    assert_get_handle(selenium, handle, "b", 1)
    check_refcount(selenium, 4)
    del handle
    check_refcount(selenium, 3)
