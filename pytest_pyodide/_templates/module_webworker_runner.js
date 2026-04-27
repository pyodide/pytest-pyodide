// Persistent worker used by BrowserWorkerRunner.
//
// Unlike module_webworker_dev.js (which loads Pyodide and runs a single
// Python script per message), this worker is a long-lived RPC endpoint:
// the main page posts {id, code} messages whose `code` is an async
// JavaScript function body. The worker evaluates it and posts back
// {id, ok, result} on success or {id, ok: false, error, stack} on error.
//
// The worker does NOT automatically load Pyodide. The main-thread runner
// sends the standard load-pyodide script as its first RPC, just like it
// would on the page. We expose ``loadPyodide`` on ``self`` so that script
// works unchanged.

// Install diagnostic handlers *before* doing anything that can throw, so
// that top-level errors (e.g. a failed `import` below) surface with a
// useful message instead of an opaque `[object Event]` on the main page.
self.addEventListener("error", (ev) => {
  // Re-post as a message so the main page always sees *something*
  // useful, even if it missed the `error` event (e.g. because the
  // listener wasn't attached yet).
  try {
    self.postMessage({
      id: -1,
      ok: false,
      error: `Worker uncaught error: ${ev.message || ""} at ${ev.filename || "?"}:${ev.lineno || 0}:${ev.colno || 0}`,
      message: ev.message || "",
      stack: (ev.error && ev.error.stack) || "",
    });
  } catch (_e) {
    // postMessage may fail if the worker is already in a bad state.
  }
});
self.addEventListener("unhandledrejection", (ev) => {
  const reason = ev.reason;
  try {
    self.postMessage({
      id: -1,
      ok: false,
      error: `Worker unhandled rejection: ${(reason && reason.message) || String(reason)}`,
      message: (reason && reason.message) || String(reason),
      stack: (reason && reason.stack) || "",
    });
  } catch (_e) {
    // ignore
  }
});

import { loadPyodide } from "./pyodide.mjs";
self.loadPyodide = loadPyodide;

self.logs = [];
for (const level of ["log", "warn", "info", "error"]) {
  const orig = console[level].bind(console);
  console[level] = function (message) {
    self.logs.push(message);
    try {
      orig(message);
    } catch (_e) {
      // ignore logging errors
    }
  };
}

onmessage = async function (e) {
  const { id, code } = e.data ?? {};
  if (typeof id === "undefined") {
    return;
  }
  try {
    // `code` is the body of an async function. It may reference `self`,
    // `pyodide`, etc. It should `return` a JSON-serializable value.
    const fn = new Function(
      "return (async () => { " + code + " })();",
    );
    const result = await fn.call(self);
    self.postMessage({ id, ok: true, result });
  } catch (err) {
    self.postMessage({
      id,
      ok: false,
      error: err?.toString?.() ?? String(err),
      message: err?.message ?? "",
      stack: err?.stack ?? "",
    });
  }
};
