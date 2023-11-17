const vm = require("vm");
const readline = require("readline");
const util = require("util");

const baseUrl = process.argv[2];
const distDir = process.argv[3];

const { loadPyodide } = require(`${distDir}/pyodide`);
process.chdir(distDir);

// node requires full paths.
function _fetch(path) {
  return fetch(new URL(path, baseUrl).toString());
}

const context = Object.assign(
  Object.create(Object.prototype, Object.getOwnPropertyDescriptors(globalThis)),
  {
    loadPyodide,
    fetch: _fetch,
    TextDecoder: util.TextDecoder,
    TextEncoder: util.TextEncoder,
  }
);
context.self = context;
vm.createContext(context);

// Get rid of all colors in output of console.log, they mess us up.
for (let key of Object.keys(util.inspect.styles)) {
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
    cur_code += line + "\n";
  } else {
    evalCode(cur_uuid, cur_code, context);
    cur_code = "";
    cur_uuid = undefined;
  }
});

async function evalCode(uuid, code, eval_context) {
  const p = new Promise((resolve, reject) => {
    eval_context.___outer_resolve = resolve;
    eval_context.___outer_reject = reject;
  });
  const wrapped_code = `
    (async function(){
        ${code}
    })().then(___outer_resolve).catch(___outer_reject);
  `;
  const delim = uuid + ":UUID";
  console.log(delim);
  try {
    vm.runInContext(wrapped_code, eval_context);
    let result = JSON.stringify(await p);
    console.log(`${delim}\n0\n${result}\n${delim}`);
  } catch (e) {
    console.log(`${delim}\n1\n${e.stack}\n${delim}`);
  }
}
console.log("READY!!");
