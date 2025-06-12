const vm = require("vm");
const readline = require("readline");
const path = require("path");
const util = require("util");

const baseUrl = process.argv[2];
const distDir = process.argv[3];
const EXTRA_GLOBALS = JSON.parse(process.env.PYTEST_PYODIDE_NODE_TEST_DRIVER_EXTRA_GLOBALS);


const { loadPyodide } = require(`${distDir}/pyodide`);
process.chdir(distDir);

// node requires full paths.
function _fetch(path, ...args) {
  return fetch(new URL(path, baseUrl).toString(), ...args);
}

const context = {
  loadPyodide,
  path,
  process,
  require,
  fetch: _fetch,
  TextDecoder,
  TextEncoder,
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
  AbortController,
  AbortSignal,
};
for (const global of EXTRA_GLOBALS) {
  context[global] = globalThis[global];
}

vm.createContext(context);
vm.runInContext("globalThis.self = globalThis;", context);

// Get rid of all colors in output of console.log, they mess us up.
for (const key of Object.keys(util.inspect.styles)) {
  util.inspect.styles[key] = undefined;
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

let cur_code = "";
let cur_uuid;
rl.on("line", async function (line) {
  if (!cur_uuid) {
    cur_uuid = line;
    return;
  }
  if (line !== cur_uuid) {
    // each line ends with an extra $, to avoid problems with end-of-line
    // translation etc.
    line = line.substring(0, line.lastIndexOf('$'))
    if(line === ""){
      cur_code += "\n";
    } else {
      cur_code += line;
    }
    // tell runner.py that the line has been read
    // so it can send the next line without worrying about
    // filling buffers
    console.log("{LINE_OK}")
  } else {
    evalCode(cur_uuid, cur_code, context);
    cur_code = "";
    cur_uuid = undefined;
  }
});

async function evalCode(uuid, code, eval_context) {
  let p = new Promise((resolve, reject) => {
    eval_context.___outer_resolve = resolve;
    eval_context.___outer_reject = reject;
  });
  let wrapped_code = `
      (async function(){
          ${code}
      })().then(___outer_resolve).catch(___outer_reject);
      `;
  let delim = uuid + ":UUID";
  console.log(delim);
  try {
    vm.runInContext(wrapped_code, eval_context, { importModuleDynamically: vm.constants?.USE_MAIN_CONTEXT_DEFAULT_LOADER });
    let result = JSON.stringify(await p);
    console.log(`${delim}\n0\n${result}\n${delim}`);
  } catch (e) {
    console.log(`${delim}\n1\n${e.stack}\n${delim}`);
  }
}
console.log("READY!!");
// evalCode("xxx", "let pyodide = await loadPyodide(); pyodide.runPython(`print([x*x+1 for x in range(10)])`);", context);
