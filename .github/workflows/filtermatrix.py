import itertools
import json
import re
import sys
from typing import Any

import yaml

# pyodide versions is a set of versions to test
# as opposed to other parameters which just filter
# the configs below
pyodide_versions = sys.argv[1]
if pyodide_versions == "*":
    pyodide_versions = "[0.22.0,0.21.0]"

matrix = yaml.safe_load(
    """
os: [ubuntu-20.04]
pyodide-version: """
    + pyodide_versions
    + """
test-config: [
    {runner: selenium, browser: firefox, browser-version: latest, driver-version: latest },
    {runner: selenium, browser: chrome, browser-version: latest, driver-version: latest },
    {runner: selenium, browser: node, browser-version: 14},
    {runner: selenium, browser: node, browser-version: 16},
    {runner: selenium, browser: node, browser-version: 18},
    {runner: selenium, browser: firefox-no-host, browser-version: latest, driver-version: latest },
    {runner: selenium, browser: host},
    # playwright browser versions are pinned to playwright version
    {runner: playwright, browser: firefox, runner-version: 1.22.0, driver-version: 18},
    {runner: playwright, browser: chrome, runner-version: 1.22.0, driver-version: 18},
]
include:
    - os: macos-11
      pyodide-version: 0.21.0
      test-config: {runner: selenium, browser: safari}
      # the following two tests check that the fallback browser behaviour works
      # okay (this is because ubuntu 22.04 doesn't support getting python 3.10.2)
    - os: ubuntu-latest
      pyodide-version: 0.21.0
      test-config: {runner: selenium, browser: node, browser-version: 18}
    - os: ubuntu-22.04
      pyodide-version: 0.21.0
      test-config: {runner: selenium, browser: node, browser-version: 18}
"""
)

ranges: "dict[str, list[tuple[str, str]]]" = {}
for key in matrix.keys():
    if key != "include":
        ranges[key] = []
        for v in matrix[key]:
            ranges[key].append((key, v))

l = list(ranges.values())

config_list: "list[dict[str, Any]]" = []
for conf in itertools.product(*l):
    dict_out = {}
    for (key, v) in conf:
        dict_out[key] = v
    config_list.append(dict_out)

if "include" in matrix:
    for inc_spec in matrix["include"]:
        config_list.append(inc_spec)


# split a comma separated string (with optional square brackets) into list
def parse_filter(s) -> "list[str]|None":
    if s.find("*") != -1:
        return None
    else:
        return [x.lower() for x in re.findall(r'[^,\'"\[\]]+', s)]


os_filter = parse_filter(sys.argv[2])
runner_filter = parse_filter(sys.argv[3])
runtime_filter = parse_filter(sys.argv[4])

filtered_configs = []
for c in config_list:
    if os_filter is None or c["os"].lower() in os_filter:
        if runner_filter is None or c["test-config"]["runner"].lower() in runner_filter:
            if (
                runtime_filter is None
                or c["test-config"]["browser"].lower() in runtime_filter
            ):
                filtered_configs.append(c)

# now output the full list of configurations as json
# which can be used in the include key in a matrix
print(f"matrix={json.dumps(filtered_configs)}")
print(f"pyodide_versions={json.dumps(matrix['pyodide-version'])}")
