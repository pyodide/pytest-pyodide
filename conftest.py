pytest_plugins = [
    "pytester",
]

# importing this fixture has a side effect of making the safari webdriver reused during the session
from pytest_pyodide import get_global_config
from pytest_pyodide.runner import use_global_safari_service  # noqa: F401


def set_configs():
    pytest_pyodide_config = get_global_config()

    pytest_pyodide_config.add_node_extra_globals(["Request", "Response"])
