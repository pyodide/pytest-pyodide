from pytest_pyodide.config import Config, get_global_config

def test_config():
    c = Config()

    runtimes = ["chrome", "firefox", "node", "safari"]

    for runtime in runtimes:
        c.get_flag(runtime)
        c.get_load_pyodide_script(runtime)

        c.set_flag(runtime, ["--headless"])
        assert c.get_flag(runtime) == ["--headless"]

        c.set_load_pyodide_script(runtime, "console.log('hello')")
        c.get_load_pyodide_script(runtime) == "console.log('hello')"
    
    c.get_initialize_script()
    c.set_initialize_script("console.log('hello')")
    assert c.get_initialize_script() == "console.log('hello')"


def test_global_config():
    assert get_global_config() is get_global_config()
