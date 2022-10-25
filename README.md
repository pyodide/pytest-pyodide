# pytest-pyodide

[![PyPI Latest Release](https://img.shields.io/pypi/v/pytest-pyodide.svg)](https://pypi.org/project/pytest-pyodide/)
![GHA](https://github.com/pyodide/pytest-pyodide/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/pyodide/pytest-pyodide/branch/main/graph/badge.svg?token=U7tWHpJj5c)](https://codecov.io/gh/pyodide/pytest-pyodide)


Pytest plugin for testing applications that use Pyodide

## Installation

pytest-pyodide requires Python 3.10+ and can be installed with
```
pip install pytest-pyodide
```
You would also one at least one of the following runtimes,
 - Chrome and chromedriver
 - Firefox and geckodriver
 - Safari and safaridriver
 - node v14+

## Usage

1. First you need a compatible version of Pyodide. You can download the Pyodide build artifacts from releases with,
   ```bash
   wget https://github.com/pyodide/pyodide/releases/download/0.21.0/pyodide-build-0.21.0.tar.bz2
   tar xjf pyodide-build-0.21.0.tar.bz2
   mv pyodide dist/
   ```

2. You can then use the provided fixtures (`selenium`, `selenium_standalone`) in tests,
   ```py
   def test_a(selenium):
       selenium.run("assert 1+1 == 2")   # run Python with Pyodide

   ```
   which you can run with
   ```bash
   pytest --dist-dir=./dist/
   ```

## `run_in_pyodide`

Some tests simply involve running a chunk of code in Pyodide and ensuring it
doesn't error. In this case, one can use the `run_in_pyodide` decorate from
`pytest_pyodide`, e.g.

```python
from pytest_pyodide import run_in_pyodide
@run_in_pyodide
def test_add(selenium):
    assert 1 + 1 == 2
```

In this case, the body of the function will automatically be run in Pyodide. The
decorator can also be called with a `packages` argument to load packages before
running the test. For example:

```python
from pytest_pyodide import run_in_pyodide
@run_in_pyodide(packages = ["regex"])
def test_regex(selenium_standalone):
    import regex
    assert regex.search("o", "foo").end() == 2
```

You can also use `@run_in_pyodide` with
`pytest.mark.parametrize`, with `hypothesis`, etc. `@run_in_pyodide` MUST be the
innermost decorator. Any decorators inside of `@run_in_pyodide` will be have no
effect on the behavior of the test.

```python
from pytest_pyodide import run_in_pyodide
@pytest.mark.parametrize("x", [1, 2, 3])
@run_in_pyodide(packages = ["regex"])
def test_type_of_int(selenium, x):
    assert type(x) is int
```

The first argument to a `@run_in_pyodide` function must be a browser runner,
generally a `selenium` fixture. The remaining arguments and the return value of
the `@run_in_pyodide` function must be picklable. The arguments will be pickled
in the host Python and unpickled in the Pyodide Python. The reverse will happen
to the return value. The first `selenium` argument will be `None` inside the
body of the function (it is used internally by the fixture). Note that a
consequence of this is that the received arguments are copies. Changes made to
an argument will not be reflected in the host Python:
```py
@run_in_pyodide
def mutate_dict(selenium, x):
    x["a"] = -1
    return x

def test_mutate_dict():
    d = {"a" : 9, "b" : 7}
    assert mutate_dict(d) == { "a" : -1, "b" : 7 }
    # d is unchanged because it was implicitly copied into the Pyodide runtime!
    assert d == {"a" : 9, "b" : 7}
```

You can also use fixtures as long as the return values of the fixtures are
picklable (most commonly, if they are `None`). As a special case, the function
will see the `selenium` fixture as `None` inside the test.

If you need to return a persistent reference to a Pyodide Python object, you can
use the special `PyodideHandle` class:
```py
@run_in_pyodide
def get_pyodide_handle(selenium):
    from pytest_pyodide.decorator import PyodideHandle
    d = { "a" : 2 }
    return PyodideHandle(d)

@run_in_pyodide
def set_value(selenium, h, key, value):
    h[key] = value

@run_in_pyodide
def get_value(selenium, h, key, value):
    return h[key]

def test_pyodide_handle(selenium):
    h = get_pyodide_handle(selenium)
    assert get_value(selenium, h, "a") == 2
    set_value(selenium, h, "a", 3)
    assert get_value(selenium, h, "a") == 3
```
This can be used to create fixtures for use with `@run_in_pyodide`.

It is possible to use `run_in_pyodide` as an inner function:

```py
def test_inner_function(selenium):
    @run_in_pyodide
    def inner_function(selenium, x):
        assert x == 6
        return 7
    assert inner_function(selenium_mock, 6) == 7
```
However, the function will not see closure variables at all:

```py
def test_inner_function_closure(selenium):
    x = 6
    @run_in_pyodide
    def inner_function(selenium):
        assert x == 6
        return 7
    # Raises `NameError: 'x' is not defined`
    assert inner_function(selenium_mock) == 7
```
Thus, the only value of inner `@run_in_pyodide` functions is to limit the scope
of the function definition. If you need a closure, you will have to wrap it in a
second function call.

## Specifying a browser

You can specify a browser runtime using `--runtime` (`--rt`) commandline option.

Possible options for `--runtime` are:

- node (default)
- firefox
- chrome
- safari
- host (do not run browser-based tests)

```sh
pytest --runtime firefox
pytest --runtime firefox --runtime chrome

# Adding -no-host suffix will disable running host tests
pytest --runtime chrome-no-host
```

## Running tests with Playwright (optional)

By default, the tests will be run with Selenium.
It is possible to run tests with [playwright](https://github.com/microsoft/playwright-python) instead as follows.

First install playwright browsers

```sh
python -m playwright install --with-deps
```

Then use the `--runner` argument to specify to run tests with playwright.

```
pytest --runner playwright
```

### Custom test marks

Custeom test marks supported by `pytest-pyodide`:

`pytest.mark.driver_timeout(timeout)`: Set script timeout in WebDriver. If the
test is known to take a long time, you can extend the deadline with this marker.

`pytest.mark.xfail_browsers(chrome="why chrome fails")`: xfail a test in
specific browsers.

## Examples

See [`examples`](./examples).

## License

pytest-pyodide uses the [Mozilla Public License Version
2.0](https://choosealicense.com/licenses/mpl-2.0/).
