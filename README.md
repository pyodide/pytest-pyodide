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
 - node v14+

## Usage

1. First you would need a compatible version of Pyodide. You can download the Pyodide build artifacts from releases with,
   ```
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

These arguments must be picklable. You can also use fixtures as long as the
return values of the fixtures are picklable (most commonly, if they are `None`).
As a special case, the function will see the `selenium` fixture as `None` inside
the test.

It is possible to use `run_in_pyodide` as an inner function:

```py
def test_inner_function(selenium):
    @run_in_pyodide
    def inner_function(selenium, x):
        assert x == 6
        return 7
    assert inner_function(selenium_mock, 6) == 7
```

Again both the arguments and return value must be pickleable.

Also, the function will not see closure variables at all:

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

## Specifying a browser

You can specify a browser runtime using `--runtime` (`--rt`) commandline option.

Possible options for `--runtime` are:

- node (default)
- firefox
- chrome
- all (chrome + firefox + node)
- host (do not run browser-based tests)

```sh
pytest --runtime firefox
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
