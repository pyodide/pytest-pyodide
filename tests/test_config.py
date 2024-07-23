from pytest_pyodide.config import Config, get_global_config


def test_config():
    c = Config()

    runtimes = ["chrome", "firefox", "node", "safari"]

    for runtime in runtimes:
        c.get_flags(runtime)
        c.get_load_pyodide_script(runtime)

        c.set_flags(runtime, ["--headless"])
        assert c.get_flags(runtime) == ["--headless"]

        c.set_load_pyodide_script(runtime, "console.log('hello')")
        assert c.get_load_pyodide_script(runtime) == "console.log('hello')"

    c.get_initialize_script()
    c.set_initialize_script("console.log('hello')")
    assert c.get_initialize_script() == "console.log('hello')"


def test_global_config():
    assert get_global_config() is get_global_config()
