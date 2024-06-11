## [0.58.0] - 2024-06-11

- Expose  AbortController and AbortSignal to the node runner.
  [#137](https://github.com/pyodide/pytest-pyodide/pull/137)

## [0.57.0] - 2024-04-30

- Fixed safari compatibility with Selenium 4.20
  [#135](https://github.com/pyodide/pytest-pyodide/pull/135)

## [0.56.1] - 2023-12-09

- Fixed a bug in webworker test template files.
  [#127](https://github.com/pyodide/pytest-pyodide/pull/127)

## [0.56.0] - 2023-12-09

- Added webworker test template files into the package.
  [#112](https://github.com/pyodide/pytest-pyodide/pull/112)

## [0.55.1] - 2023-11-17

- Reverted [#121](https://github.com/pyodide/pytest-pyodide/pull/121)

## [0.55.0] - 2023-11-17

- If Pyodide includes tblib 3.0, pytest-pyodide will now use it correctly.
  [#122](https://github.com/pyodide/pytest-pyodide/pull/122)

- The entire node global scope is now included in the node runner, whereas
  previously we included the minimal set of names that were needed for Pyodide
  to run.
  [#121](https://github.com/pyodide/pytest-pyodide/pull/121)

- Added support for running doctests in Pyodide if they have
  `# doctest: +RUN_IN_PYODIDE` on the first line.
  [#117](https://github.com/pyodide/pytest-pyodide/pull/117)

- Added support in `@run_in_pyodide` for arbitrary function definitions,
  including positional only and keyword only arguments, varargs and kwargs, type
  annotations, and argument default values.
  [#116](https://github.com/pyodide/pytest-pyodide/pull/116)
  [#119](https://github.com/pyodide/pytest-pyodide/pull/119)


## [0.54.0] - 2023-11-04

- BREAKING: dropped support for Node < 18.
  [#113](https://github.com/pyodide/pytest-pyodide/pull/113)

## [0.53.1] - 2023-10-10

- Removed the ctypes dependency so it can be used with Python builds with
  dynamic linking disabled.
  [#110](https://github.com/pyodide/pytest-pyodide/pull/110)

## [0.53.0] - 2023-08-29

- The Github reusable workflow `testall.yaml` does not accept asterisks ("*") in parameters.
  If you want to use the default value, you can omit the parameter.
  [#86](https://github.com/pyodide/pytest-pyodide/pull/86)

- The Github reusable workflow `testall.yaml` now receives parameters without square brackets.
  [#86](https://github.com/pyodide/pytest-pyodide/pull/86)


## [0.52.2] - 2023-06-18

- Added compatibility for a lock file named `pyodide-lock.json` in addition to
  `repodata.json`.
  [#96](https://github.com/pyodide/pytest-pyodide/pull/96)

- Don't use the deprecated `pyodide.isPyProxy` API when `pyodide.ffi.PyProxy` is
  available.
  [#97](https://github.com/pyodide/pytest-pyodide/pull/96)


## [0.52.1] - 2023-06-10

- Removed use of `executable_path` from selenium driver construction to make
  pytest-pyodide compatible with Selenium v4.10.
  [#93](https://github.com/pyodide/pytest-pyodide/pull/93)


## [0.52.0] - 2023-06-01

- Removed `JsException` unpickle special case. This was fixed by
  [pyodide/pyodide#3387](https://github.com/pyodide/pyodide/pull/3387).
  [#91](https://github.com/pyodide/pytest-pyodide/pull/91)

- Dropped support for Pyodide version `0.21.x`.
  [#91](https://github.com/pyodide/pytest-pyodide/pull/91)

## [0.51.0] - 2023-05-10

- Added test templates files in the package.
  [#87](https://github.com/pyodide/pytest-pyodide/pull/87)

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
