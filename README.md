# pytest-pyodide

[![PyPI Latest Release](https://img.shields.io/pypi/v/pytest-pyodide.svg)](https://pypi.org/project/pytest-pyodide/)
![GHA](https://github.com/pyodide/pytest-pyodide/actions/workflows/build.yml/badge.svg)
[![codecov](https://codecov.io/gh/pyodide/pytest-pyodide/branch/main/graph/badge.svg?token=U7tWHpJj5c)](https://codecov.io/gh/pyodide/pytest-pyodide)


Pytest plugin for testing applications that use Pyodide

## Installation

pytest-pyodide requires Python 3.10+ and can be installed with
```
pip install pytest-pyodide
```
You would also need one at least one of the following runtimes:
 - Chrome and chromedriver
 - Firefox and geckodriver
 - Safari and safaridriver
 - node v18+

## Github Reusable workflow

pytest-pyodide also supports testing on github actions by means of a reusable workflow in [/.github/workflows/main.yml](/.github/workflows/main.yml) This allows you to test on a range of browser/OS combinations without having to install all the testing stuff, and integrate it easily into your CI process.

In your github actions workflow, call it with as a aseparate job. To pass in your build wheel use an upload-artifact step in your build step.

This will run your tests on the given browser/pyodide version/OS configuration. It runs pytest in the root of your repo, which should catch any test_\*.py files in subfolders.

```
jobs:
  # Build for pyodide 0.24.1
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: 3.11
    - uses: mymindstorm/setup-emsdk@v11
      with:
        version: 3.1.45
    - run: pip install pyodide-build==0.24.1
    - run: pyodide build
    - uses: actions/upload-artifact@v3
      with:
        name: pyodide wheel
        path: dist
  # this is the job which you add to run pyodide-test
  test:
    needs: build
    uses: pyodide/pytest-pyodide/.github/workflows/main.yaml@main
    with:
      build-artifact-name: pyodide wheel
      build-artifact-path: dist
      browser: firefox
      runner: selenium
      pyodide-version: 0.24.1
```

If you want to run on multiple browsers / pyodide versions etc., you can either use a matrix strategy and run main.yaml as above, or you can use testall.yaml. This by default tests on all browsers (and node) with multiple configurations. If you want to reduce the configurations you can filter with lists of browsers, runners, pyodide-versions as shown below.
```
  test:
    needs: build
    uses: pyodide/pytest-pyodide/.github/workflows/testall.yaml@main
    with:
      build-artifact-name: pyodide wheel
      build-artifact-path: dist
      pyodide-versions: "0.23.4, 0.24.1"
      runners: "selenium, playwright"
      browsers: "firefox, chrome, node"
      os: "ubuntu-latest, macos-latest"
```

## Usage

1. First you need a compatible version of Pyodide. You can download the Pyodide build artifacts from releases with,
   ```bash
   wget https://github.com/pyodide/pyodide/releases/download/0.24.1/pyodide-build-0.24.1.tar.bz2
   tar xjf pyodide-build-0.24.1.tar.bz2
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
def get_value(selenium, h, key):
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

## Copying files to Pyodide

You can copy files to the pyodide filesystem using the `copy_files_to_pyodide` decorator. This takes two arguments - a list of `(src,destination)` pairs. These can be any of: 1) A filename, 2) A folder name, which is copied to the destination path (along with all subdirectories if `recurse_directories` is True), 3) A glob pattern, which will fetch all files matching the pattern and copy them to a destination directory, whilst preserving the folder structure.

If you set `install_wheels` to True, any `.whl` files will be installed on pyodide. This is useful for installing your package.

```py
from pytest_pyodide.decorator import copy_files_to_pyodide

@copy_files_to_pyodide(file_list=[(src,dest)],install_wheels=True,recurse_directories=True)
```


## Running non-pyodide tests in Pyodide

This plugin also supports running standard pytest tests on pyodide in a browser. So if you have an existing codebase and
you want to check if your pyodide build works, just run it like this:
```
# Make the emscripten/wasm32  wheel in the dist folder
pyodide build
# the following code
# a) copies the test_path directory and subfolders to a Pyodide instance, and
# b) installs any wheels in the dist subfolder so that this package is available on the Pyodide VM
pytest --run-in-pyodide test_path --runtime <runtime> --dist-dir=<pyodide/dist>
```

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

Custom test marks supported by `pytest-pyodide`:

`pytest.mark.driver_timeout(timeout)`: Set script timeout in WebDriver. If the
test is known to take a long time, you can extend the deadline with this marker.

`pytest.mark.xfail_browsers(chrome="why chrome fails")`: xfail a test in
specific browsers.

## Examples

See [`examples`](./examples).


## Compatible Pyodide versions

See [`compatibility table`](./COMPATIBILITY.md).

## License

pytest-pyodide uses the [Mozilla Public License Version
2.0](https://choosealicense.com/licenses/mpl-2.0/).
