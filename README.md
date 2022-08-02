# pytest-pyodide

![GHA](https://github.com/pyodide/pytest-pyodide/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/pyodide/pytest-pyodide/branch/main/graph/badge.svg?token=U7tWHpJj5c)](https://codecov.io/gh/pyodide/pytest-pyodide)


Pytest plugin for testing Pyodide and third-party applications that use Pyodide

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
   wget https://github.com/pyodide/pyodide/releases/download/0.21.0a3/pyodide-build-0.21.0a3.tar.bz2
   tar xjf pyodide-build-0.21.0a3.tar.bz2
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
3. For convenience, the `run_in_pyodide` decorator is also provided. For
   instance the above example would be equivalent to,
   ```py
   from pytest_pyodide import run_in_pyodide

   @run_in_pyodide
   def test_a(selenium):
       assert 1+1 == 2


   If there are packages required for a test,
   you need to add them to the `packages` argument.

   ```py
   @run_in_pyodide(packages=["numpy"])
   def test_numpy(selenium):
       assert sum(numpy.zeros()) == 0.0
   ```

## Specifying a browser

You can specify a browser runtime using `--runtime` (`--rt`) commandline option.

Possible options for `--runtime` are:

- node (default)
- firefox
- chrome
- all (chrome + firefox + node)
- host (do not run browser based-tests)

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

Then use the --runner argument to specify to run tests with playwright.

```
pytest --runner playwright
```

## License

pytest-pyodide uses the [Mozilla Public License Version
2.0](https://choosealicense.com/licenses/mpl-2.0/).
