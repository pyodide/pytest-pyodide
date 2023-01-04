## [0.50.0] - 2023-01-05

- Add auto-setting of python version and runner version based on pyodide version.
  [#66](https://github.com/pyodide/pytest-pyodide/pull/66)

- Add support for custom headers in the pytest web server code, by setting
  the `extra_headers` parameter in the `spawn_web_server` function.
  [#39](https://github.com/pyodide/pytest-pyodide/pull/39)

- Breaking: removed STANDALONE_REFRESH env variable which was used to
  override `selenium_standalone` fixture with `selenium_standalone_refresh`.
  [#65](https://github.com/pyodide/pytest-pyodide/pull/65)

- Added command line option `--run-in-pyodide`. This will run a set of normal pytest tests in pyodide using the
  same testing architecture used for running dedicated pyodide tests.
  [#62](https://github.com/pyodide/pytest-pyodide/pull/62)

- Breaking: `--runtime` commandline flag now requires runtimes to be comma-separated.
  [#76](https://github.com/pyodide/pytest-pyodide/pull/76)

- Add support for a custom `SimpleHTTPRequestHandler` class in the pytest
  webserver code, by passing the `handler_cls` parameter in the
  `spawn_web_server` function.
  [#47](https://github.com/pyodide/pytest-pyodide/pull/47)

## [0.23.2] - 2022-11-14

- Fixes for Python 3.11: there are some bugs with `ast.fix_missing_locations` in
  Python 3.11.0.
  [#60](https://github.com/pyodide/pytest-pyodide/pull/60)

## [0.23.1] - 2022.10.26

- Breaking: altered the way that `PyodideHandle` is received inside the Pyodide
  function so that it is transparent to the callee: the handle is automatically
  converted into the wrapped object.
  [#54](https://github.com/pyodide/pytest-pyodide/pull/54)

## [0.23.0] - 2022.10.24

- `JsException` raise from within pyodide is now unpickled correctly in the host. ([#45](https://github.com/pyodide/pytest-pyodide/issues/45))
- Improve error messages when unpickling error messages with objects that don't exist in the host environment
   ([#46](https://github.com/pyodide/pytest-pyodide/issues/46))
- Added the `PyodideHandle` class which allows returning a reference to a Python
  object in the Pyodide runtime from a `@run_in_pyodide` function. This is
  useful for fixtures designed to be used with `@run_in_pyodide`.
  ([#49](https://github.com/pyodide/pytest-pyodide/issues/49))

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
