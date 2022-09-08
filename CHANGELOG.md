## [0.22.2] - 2022.09.08

- Host tests will now run by default. If you want to disable running host tests, add `-no-host` suffix in the `--runtime` option. ([#33](https://github.com/pyodide/pytest-pyodide/pull/33))
- Multiple browser testing is now available by passing `--runtime` option multiple times. ([#33](https://github.com/pyodide/pytest-pyodide/pull/33))

## [0.22.1] - 2022.09.06

- Re-order safari tests to make sure only one simultaneous session exists during the test ([#29](https://github.com/pyodide/pytest-pyodide/pull/29))

## [0.22.0] - 2022.09.02

- Add `selenium_standalone_refresh` fixture ([#27](https://github.com/pyodide/pytest-pyodide/pull/27))
- Add selenium safari support ([#27](https://github.com/pyodide/pytest-pyodide/pull/27))

## [0.21.1] - 2022.08.10

- Use forked tblib and clean up tracebacks ([#22](https://github.com/pyodide/pytest-pyodide/pull/22))


## [0.21.0] - 2022.08.05

- A first stable release of `pytest-pyodide`.
