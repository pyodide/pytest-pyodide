from importlib.metadata import PackageNotFoundError, version

from .browser import (
    BrowserWrapper,
    NodeWrapper,
    PlaywrightChromeWrapper,
    PlaywrightFirefoxWrapper,
    PlaywrightWrapper,
    SeleniumChromeWrapper,
    SeleniumFirefoxWrapper,
    SeleniumWrapper,
)
from .decorator import run_in_pyodide
from .fixture import *  # noqa: F403, F401
from .server import spawn_web_server
from .utils import parse_driver_timeout, set_webdriver_script_timeout

try:
    __version__ = version("pytest-pyodide")
except PackageNotFoundError:
    # package is not installed
    pass

__all__ = [
    "BrowserWrapper",
    "SeleniumWrapper",
    "PlaywrightWrapper",
    "SeleniumFirefoxWrapper",
    "SeleniumChromeWrapper",
    "PlaywrightChromeWrapper",
    "PlaywrightFirefoxWrapper",
    "NodeWrapper",
    "set_webdriver_script_timeout",
    "parse_driver_timeout",
    "run_in_pyodide",
    "spawn_web_server",
]
