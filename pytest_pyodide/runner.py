import json
import textwrap
from pathlib import Path

import pexpect
import pytest

CHROME_FLAGS: list[str] = ["--js-flags=--expose-gc"]
FIREFOX_FLAGS: list[str] = []
NODE_FLAGS: list[str] = []


TEST_SETUP_CODE = """
Error.stackTraceLimit = Infinity;

// Fix globalThis is messed up in firefox see facebook/react#16606.
// Replace it with window.
globalThis.globalThis = globalThis.window || globalThis;

globalThis.sleep = function (s) {
    return new Promise((resolve) => setTimeout(resolve, s));
};

globalThis.assert = function (cb, message = "") {
    if (message !== "") {
        message = "\\n" + message;
    }
    if (cb() !== true) {
        throw new Error(
            `Assertion failed: ${cb.toString().slice(6)}${message}`
        );
    }
};

globalThis.assertAsync = async function (cb, message = "") {
    if (message !== "") {
        message = "\\n" + message;
    }
    if ((await cb()) !== true) {
        throw new Error(
            `Assertion failed: ${cb.toString().slice(12)}${message}`
        );
    }
};

function checkError(err, errname, pattern, pat_str, thiscallstr) {
    if (typeof pattern === "string") {
        pattern = new RegExp(pattern);
    }
    if (!err) {
        throw new Error(`${thiscallstr} failed, no error thrown`);
    }
    if (err.constructor.name !== errname) {
        throw new Error(
            `${thiscallstr} failed, expected error ` +
                `of type '${errname}' got type '${err.constructor.name}'`
        );
    }
    if (!pattern.test(err.message)) {
        throw new Error(
            `${thiscallstr} failed, expected error ` +
                `message to match pattern ${pat_str} got:\n${err.message}`
        );
    }
}

globalThis.assertThrows = function (cb, errname, pattern) {
    let pat_str = typeof pattern === "string" ? `"${pattern}"` : `${pattern}`;
    let thiscallstr = `assertThrows(${cb.toString()}, "${errname}", ${pat_str})`;
    let err = undefined;
    try {
        cb();
    } catch (e) {
        err = e;
    }
    checkError(err, errname, pattern, pat_str, thiscallstr);
};

globalThis.assertThrowsAsync = async function (cb, errname, pattern) {
    let pat_str = typeof pattern === "string" ? `"${pattern}"` : `${pattern}`;
    let thiscallstr = `assertThrowsAsync(${cb.toString()}, "${errname}", ${pat_str})`;
    let err = undefined;
    try {
        await cb();
    } catch (e) {
        err = e;
    }
    checkError(err, errname, pattern, pat_str, thiscallstr);
};
""".strip()

INITIALIZE_SCRIPT = "pyodide.runPython('');"


class JavascriptException(Exception):
    def __init__(self, msg, stack):
        self.msg = msg
        self.stack = stack
        # In chrome the stack contains the message
        if self.stack and self.stack.startswith(self.msg):
            self.msg = ""

    def __str__(self):
        return "\n\n".join(x for x in [self.msg, self.stack] if x)


class _BrowserBaseRunner:
    browser = ""
    script_timeout = 20
    JavascriptException = JavascriptException

    def __init__(
        self,
        server_port,
        server_hostname="127.0.0.1",
        server_log=None,
        load_pyodide=True,
        script_type="classic",
        dist_dir=None,
        jspi=False,
        *args,
        **kwargs,
    ):
        self.server_port = server_port
        self.server_hostname = server_hostname
        self.base_url = f"http://{self.server_hostname}:{self.server_port}"
        self.server_log = server_log
        self.script_type = script_type
        self.dist_dir = dist_dir
        self.driver = self.get_driver(jspi)
        self.set_script_timeout(self.script_timeout)
        self.prepare_driver()
        self.javascript_setup()
        if load_pyodide:
            self.load_pyodide()
            self.initialize_pyodide()
            self.save_state()
            self.restore_state()

    def get_driver(self, jspi=False):
        raise NotImplementedError()

    def goto(self, page):
        raise NotImplementedError()

    def set_script_timeout(self, timeout):
        raise NotImplementedError()

    def quit(self):
        raise NotImplementedError()

    def refresh(self):
        raise NotImplementedError()

    def run_js_inner(self, code, check_code):
        raise NotImplementedError()

    def prepare_driver(self):
        if self.script_type == "classic":
            self.goto(f"{self.base_url}/test.html")
        elif self.script_type == "module":
            self.goto(f"{self.base_url}/module_test.html")
        else:
            raise Exception("Unknown script type to load!")

    def javascript_setup(self):
        self.run_js(
            TEST_SETUP_CODE,
            pyodide_checks=False,
        )

    def load_pyodide(self):
        self.run_js(
            """
            let pyodide = await loadPyodide({ fullStdLib: false, jsglobals : self });
            self.pyodide = pyodide;
            globalThis.pyodide = pyodide;
            pyodide._api.inTestHoist = true; // improve some error messages for tests
            """
        )

    def initialize_pyodide(self):
        self.run_js(
            """
            let isPyProxy;
            if(pyodide.ffi) {
                isPyProxy = (o) => o instanceof pyodide.ffi.PyProxy;
            } else {
                isPyProxy = pyodide.isPyProxy;
            }
            pyodide.$handleTestResult = function(result) {
                if(!(result && result.toJs)){
                    return result;
                }
                let converted_result = result.toJs();
                if(isPyProxy(converted_result)){
                    converted_result = undefined;
                }
                result.destroy();
                return converted_result;
            }
            """
        )
        self.run_js(INITIALIZE_SCRIPT)
        from .decorator import initialize_decorator

        initialize_decorator(self)

    @property
    def pyodide_loaded(self):
        return self.run_js("return !!(self.pyodide && self.pyodide.runPython);")

    @property
    def logs(self):
        logs = self.run_js("return self.logs;", pyodide_checks=False)
        if logs is not None:
            return "\n".join(str(x) for x in logs)
        return ""

    def clean_logs(self):
        self.run_js("self.logs = []", pyodide_checks=False)

    def run(self, code):
        return self.run_js(
            f"""
            let result = pyodide.runPython({code!r});
            return pyodide.$handleTestResult(result);
            """
        )

    def run_async(self, code):
        return self.run_js(
            f"""
            await pyodide.loadPackagesFromImports({code!r})
            let result = await pyodide.runPythonAsync({code!r});
            return pyodide.$handleTestResult(result);
            """
        )

    def run_js(self, code, pyodide_checks=True):
        """Run JavaScript code and check for pyodide errors"""
        if isinstance(code, str) and code.startswith("\n"):
            # we have a multiline string, fix indentation
            code = textwrap.dedent(code)

        if pyodide_checks:
            check_code = """
                    if(globalThis.pyodide && pyodide._module && pyodide._module._PyErr_Occurred()){
                        try {
                            pyodide._module._pythonexc2js();
                        } catch(e){
                            console.error(`Python exited with error flag set! Error was:\n${e.message}`);
                            // Don't put original error message in new one: we want
                            // "pytest.raises(xxx, match=msg)" to fail
                            throw new Error(`Python exited with error flag set!`);
                        }
                    }
           """
        else:
            check_code = ""
        return self.run_js_inner(code, check_code)

    def get_num_hiwire_keys(self):
        return self.run_js("return pyodide._module.hiwire.num_keys();")

    @property
    def force_test_fail(self) -> bool:
        return self.run_js("return !!pyodide._api.fail_test;")

    def clear_force_test_fail(self):
        self.run_js("pyodide._api.fail_test = false;")

    def save_state(self):
        self.run_js("self.__savedState = pyodide._api.saveState();")

    def restore_state(self):
        self.run_js(
            """
            if(self.__savedState){
                pyodide._api.restoreState(self.__savedState)
            }
            """
        )

    def get_num_proxies(self):
        return self.run_js("return pyodide._module.pyproxy_alloc_map.size")

    def enable_pyproxy_tracing(self):
        self.run_js("pyodide._module.enable_pyproxy_allocation_tracing()")

    def disable_pyproxy_tracing(self):
        self.run_js("pyodide._module.disable_pyproxy_allocation_tracing()")

    def run_webworker(self, code):
        if isinstance(code, str) and code.startswith("\n"):
            # we have a multiline string, fix indentation
            code = textwrap.dedent(code)

        worker_file = (
            "webworker_dev.js"
            if self.script_type == "classic"
            else "module_webworker_dev.js"
        )

        return self.run_js(
            """
            let worker = new Worker('{}', {{ type: '{}' }});
            let res = new Promise((res, rej) => {{
                worker.onerror = e => rej(e);
                worker.onmessage = e => {{
                    if (e.data.results) {{
                       res(e.data.results);
                    }} else {{
                       rej(e.data.error);
                    }}
                }};
                worker.postMessage({{ python: {!r} }});
            }});
            return await res
            """.format(
                f"http://{self.server_hostname}:{self.server_port}/{worker_file}",
                self.script_type,
                code,
            ),
            pyodide_checks=False,
        )

    def load_package(self, packages):
        self.run_js(f"await pyodide.loadPackage({packages!r})")


class _SeleniumBaseRunner(_BrowserBaseRunner):
    def goto(self, page):
        self.driver.get(page)

    def set_script_timeout(self, timeout):
        self.driver.set_script_timeout(timeout)
        self.script_timeout = timeout

    def quit(self):
        self.driver.quit()

    def refresh(self):
        self.driver.refresh()
        self.javascript_setup()

    def run_js_inner(self, code, check_code):
        wrapper = """
            let cb = arguments[arguments.length - 1];
            let run = async () => { %s }
            (async () => {
                try {
                    let result = await run();
                    %s
                    cb([0, result]);
                } catch (e) {
                    cb([1, e.toString(), e.stack, e.message]);
                }
            })()
        """
        retval = self.driver.execute_async_script(wrapper % (code, check_code))
        if retval[0] == 0:
            return retval[1]
        else:
            print("JavascriptException message: ", retval[3])
            raise JavascriptException(retval[1], retval[2])

    @property
    def urls(self):
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            yield self.driver.current_url


class _PlaywrightBaseRunner(_BrowserBaseRunner):
    def __init__(self, browsers, *args, **kwargs):
        self.browsers = browsers
        super().__init__(*args, **kwargs)

    def goto(self, page):
        self.driver.goto(page)

    def get_driver(self, jspi=False):
        if jspi:
            raise NotImplementedError("JSPI not supported with playwright")
        return self.browsers[self.browser].new_page()

    def set_script_timeout(self, timeout):
        # playwright uses milliseconds for timeout
        self.driver.set_default_timeout(timeout * 1000)

    def quit(self):
        self.driver.close()

    def refresh(self):
        self.driver.reload()
        self.javascript_setup()

    def run_js_inner(self, code, check_code):
        # playwright `evaluate` waits until primise to resolve,
        # so we don't need to use a callback like selenium.
        wrapper = """
            let run = async () => { %s }
            (async () => {
                try {
                    let result = await run();
                    %s
                    return [0, result];
                } catch (e) {
                    return [1, e.toString(), e.stack];
                }
            })()
        """
        retval = self.driver.evaluate(wrapper % (code, check_code))
        if retval[0] == 0:
            return retval[1]
        else:
            raise JavascriptException(retval[1], retval[2])


class SeleniumFirefoxRunner(_SeleniumBaseRunner):
    browser = "firefox"

    def get_driver(self, jspi=False):
        if jspi:
            raise NotImplementedError("JSPI not supported in Firefox")
        from selenium.webdriver import Firefox
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

        options = Options()
        options.add_argument("--headless")
        for flag in FIREFOX_FLAGS:
            options.add_argument(flag)

        return Firefox(service=Service(), options=options)


class SeleniumChromeRunner(_SeleniumBaseRunner):
    browser = "chrome"

    def get_driver(self, jspi=False):
        from selenium.webdriver import Chrome
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        if jspi:
            options.add_argument("--enable-features=WebAssemblyExperimentalJSPI")
            options.add_argument("--enable-experimental-webassembly-features")
        for flag in CHROME_FLAGS:
            options.add_argument(flag)
        return Chrome(options=options)

    def collect_garbage(self):
        self.driver.execute_cdp_cmd("HeapProfiler.collectGarbage", {})


# Stopping and starting the safari webdriver multiple times during the test
# often causes unexpected errors. So we make a global webdriver instance and
# reuse it.
GLOBAL_SAFARI_WEBDRIVER = None


@pytest.fixture(scope="session", autouse=True)
def use_global_safari_service():
    if "safari" in pytest.pyodide_runtimes:
        global GLOBAL_SAFARI_WEBDRIVER

        from selenium.webdriver.common.driver_finder import DriverFinder
        from selenium.webdriver.safari.options import Options
        from selenium.webdriver.safari.service import Service

        GLOBAL_SAFARI_WEBDRIVER = Service(reuse_service=True)

        try:
            # selenium >= 4.20
            # https://github.com/SeleniumHQ/selenium/pull/13387
            finder = DriverFinder(GLOBAL_SAFARI_WEBDRIVER, Options())
            browser_path = finder.get_driver_path()
        except Exception:
            # selenium < 4.20
            browser_path = DriverFinder.get_path(GLOBAL_SAFARI_WEBDRIVER, Options())

        GLOBAL_SAFARI_WEBDRIVER.path = browser_path
        GLOBAL_SAFARI_WEBDRIVER.start()

        try:
            yield GLOBAL_SAFARI_WEBDRIVER
        finally:
            GLOBAL_SAFARI_WEBDRIVER.stop()
    else:
        yield None


class SeleniumSafariRunner(_SeleniumBaseRunner):
    browser = "safari"
    script_timeout = 30

    def get_driver(self, jspi=False):
        if jspi:
            raise NotImplementedError("JSPI not supported in Firefox")
        from selenium.webdriver import Safari
        from selenium.webdriver.safari.options import Options

        options = Options()
        if GLOBAL_SAFARI_WEBDRIVER is not None:
            instance = Safari(
                options=options,
                service=GLOBAL_SAFARI_WEBDRIVER,
            )
        else:
            instance = Safari(options=options)

        return instance


class PlaywrightChromeRunner(_PlaywrightBaseRunner):
    browser = "chrome"

    def collect_garbage(self):
        client = self.driver.context.new_cdp_session(self.driver)
        client.send("HeapProfiler.collectGarbage")


class PlaywrightFirefoxRunner(_PlaywrightBaseRunner):
    browser = "firefox"


class NodeRunner(_BrowserBaseRunner):
    browser = "node"

    def init_node(self, jspi=False):
        curdir = Path(__file__).parent
        self.p = pexpect.spawn("/bin/bash", timeout=60)
        self.p.setecho(False)
        self.p.delaybeforesend = None
        # disable canonical input processing mode to allow sending longer lines
        # See: https://pexpect.readthedocs.io/en/stable/api/pexpect.html#pexpect.spawn.send
        self.p.sendline("stty -icanon")

        node_version = pexpect.spawn("node --version").read().decode("utf-8")
        node_major = int(node_version.split(".")[0][1:])  # vAA.BB.CC -> AA
        if node_major < 18:
            raise RuntimeError(
                f"Node version {node_version} is too old, please use node >= 18"
            )

        extra_args = NODE_FLAGS[:]
        # Node v14 require the --experimental-wasm-bigint which
        # produces errors on later versions
        if jspi:
            extra_args.append("--experimental-wasm-stack-switching")

        self.p.sendline(
            f"node --expose-gc {' '.join(extra_args)} {curdir}/node_test_driver.js {self.base_url} {self.dist_dir}",
        )

        try:
            self.p.expect_exact("READY!!")
        except (pexpect.exceptions.EOF, pexpect.exceptions.TIMEOUT):
            raise JavascriptException("", self.p.before.decode()) from None

    def get_driver(self, jspi=False):
        self._logs = []
        self.init_node(jspi)

        class NodeDriver:
            def __getattr__(self, x):
                raise NotImplementedError()

        return NodeDriver()

    def prepare_driver(self):
        pass

    def set_script_timeout(self, timeout):
        self.script_timeout = timeout

    def quit(self):
        self.p.sendeof()

    def refresh(self):
        self.quit()
        self.init_node()
        self.javascript_setup()

    def collect_garbage(self):
        self.run_js("gc()")

    @property
    def logs(self):
        return "\n".join(self._logs)

    def clean_logs(self):
        self._logs = []

    def run_js_inner(self, code, check_code):
        check_code = ""
        wrapped = """
            let result = await (async () => {{ {} }})();
            {}
            return result;
        """.format(
            code,
            check_code,
        )
        from uuid import uuid4

        cmd_id = str(uuid4())
        self.p.sendline(cmd_id)
        self.p.sendline(wrapped)
        self.p.sendline(cmd_id)
        self.p.expect_exact(f"{cmd_id}:UUID\r\n", timeout=self.script_timeout)
        self.p.expect_exact(f"{cmd_id}:UUID\r\n")
        if self.p.before:
            self._logs.append(self.p.before.decode()[:-2].replace("\r", ""))
        self.p.expect("[01]\r\n")
        success = int(self.p.match[0].decode()[0]) == 0
        self.p.expect_exact(f"\r\n{cmd_id}:UUID\r\n")
        if success:
            return json.loads(self.p.before.decode().replace("undefined", "null"))
        else:
            raise JavascriptException("", self.p.before.decode())
