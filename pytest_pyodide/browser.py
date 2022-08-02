import warnings

from . import runner

warnings.simplefilter("always", DeprecationWarning)
warnings.warn(
    "pytest_pyodide.browser has been renamed to the pytest_pyodide.runner",
    DeprecationWarning,
)


def __setattr__(name, value):
    setattr(runner, name, value)


def __getattr__(name):
    return getattr(runner, name)
