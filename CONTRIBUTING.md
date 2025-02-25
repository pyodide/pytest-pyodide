## Running the tests

`pytest-pyodide` supports following runners and runtimes:

- selenium - chrome
- selenium - firefox
- selenium - safari (macOS only)
- node.js
- playwright - chromium
- playwright - firefox

We run all possible combinations of runners and runtimes in the CI, so it is not necessary to run all of them locally.
However, we recommend running at least one of the combinations locally to ensure that the tests pass before submitting a PR.

> Note: As of 2025/02, playwright runners have performance issues and are disabled in CI. We recommend using selenium runners for now.

Here are the steps to setup runners and runtimes and run the tests locally:

### 0. Install pytest-pyodide and Pyodide distribution

First, install `pytest-pyodide` and the target Pyodide distribution.

The latest `pytest-pyodide` is expected to be compatible with the latest few Pyodide distributions (See the [COMPATIBILITY.md](COMPATIBILITY.md) for more details).
So if you have a specific target Pyodide version, you can use that Pyodide version. Otherwise, we recommend using the latest stable Pyodide version.

```bash
# Install pytest-pyodide with test dependencies
pip install -e ".[test]"

# Download the target Pyodide distribution, for example, 0.27.2
export PYODIDE_VERSION="0.27.2"
wget https://github.com/pyodide/pyodide/releases/download/${PYODIDE_VERSION}/pyodide-${PYODIDE_VERSION}.tar.bz2
# unpack the distribution, this will create a `pyodide` directory in the current directory
# if not, please check the directory name and rename it to `pyodide`
tar -xf pyodide-${PYODIDE_VERSION}.tar.bz2

# Install `pyodide-py` package with the target Pyodide version
pip install "pyodide-py==${PYODIDE_VERSION}"
```

### 1. Install runtimes

#### 1.1. Install node.js

Installing Node.js is easy compared to other runtimes.
So unless you have a specific reason to use other runtimes, such as fixing a bug in Chrome or Firefox,
using Node.js is recommended.

Install Node.js by following the instructions on the [official website](https://nodejs.org/),
or use [nvm](https://github.com/nvm-sh/nvm) if you don't want to change the global Node.js version
After the installation, `node` executable should be available in your PATH.

Using the latest LTS version of Node.js is recommended.

#### 1.2 Install browsers and WebDrivers for Selenium

[Selenium](https://www.selenium.dev/) is a primary runner for `pytest-pyodide`,
and it requires browser runtimes and corresponding WebDrivers to run.

Luckily, `selenium>4.0` has built-in support for installing browsers and WebDrivers: [selenium-manager](https://www.selenium.dev/documentation/selenium_manager/).
Therefore, it is normally not necessary to install browsers and WebDrivers manually.
The selenium manager will download the necessary binaries automatically.

However, if you want to use your own browser or WebDriver, you can install them manually.

- Chrome
  - You can download chrome and chromedriver from the [chrome-for-testing](https://github.com/GoogleChromeLabs/chrome-for-testing) repository.
- Firefox
  - You can download geckodriver from the following repository: https://github.com/mozilla/geckodriver.
  - Firefox does not support official ways to download older versions, but you can find them in the following link:
    - `https://download-installer.cdn.mozilla.net/pub/firefox/releases/{{FIREFOX_VERSION}}/linux-x86_64/en-US/firefox-{{FIREFOX_VERSION}}.tar.bz2`
    - replace the `{{FIREFOX_VERSION}}` with the target version, for example, `133.0` for Firefox 133

> [!TIP]
> You can pass `SE_BROWSER_VERSION` environment variables to the test command to specify the browser and driver versions.
> For example, `SE_BROWSER_VERSION=125 pytest -v --runtime=firefox` will use Firefox 133.

#### 1.3. Install browsers for Playwright

[Playwright](https://playwright.dev/) is a browser automation library that
is based on the Chrome dev tools, but it also supports firefox (by patching the browser runtime).
It is a secondary runner for `pytest-pyodide`, which is less stable than Selenium.

Playwright has built-in support for installing browsers.
You can install browsers by running the following command:

```bash
# playwright executable should be available after installing pytest-pyodide,
# if not, try python -m playwright instead

# chrome
playwright install chrome --with-deps

# firefox
playwright install firefox --with-deps
```

Unfortunately, some OSes might not support these commands.
In that case, you should search a way to handle it in the Playwright issue tracker.

### 2. Running the tests

After installing the runtimes, you can run the tests with the following command:

```bash
# Node
pytest -v --runtime=node

# Selenium - Chrome / Firefox
pytest -v --runtime=chrome
pytest -v --runtime=firefox

# Playwright - Chrome / Firefox
pytest -v --runner=playwright --runtime=chrome
pytest -v --runner=playwright --runtime=firefox
```
