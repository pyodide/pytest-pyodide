pytest_plugins = [
    "pytester",
]

# importing this fixture has a side effect of making the safari webdriver reused during the session
from pytest_pyodide.runner import use_global_safari_service  # noqa: F401
