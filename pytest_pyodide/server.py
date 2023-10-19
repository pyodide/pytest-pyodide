import contextlib
import functools
import http.server
import multiprocessing
import os
import pathlib
import queue
import shutil
import socketserver
import sys
import tempfile
from io import BytesIO


@functools.cache
def _default_templates() -> dict[str, bytes]:
    templates_dir = pathlib.Path(__file__).parent / "_templates"

    templates = {}
    template_files = list(templates_dir.glob("*.html")) + list(
        templates_dir.glob("*.js")
    )
    for template_file in template_files:
        templates[f"/{template_file.name}"] = template_file.read_bytes()

    return templates


class DefaultHandler(http.server.SimpleHTTPRequestHandler):
    default_templates = _default_templates()

    def __init__(self, *args, **kwargs):
        self.extra_headers = kwargs.pop("extra_headers", {})
        super().__init__(*args, **kwargs)

    def log_message(self, format_, *args):
        print(
            "[%s] source: %s:%s - %s"
            % (
                self.log_date_time_string(),
                *self.client_address,
                format_ % args,
            )
        )

    def get_template(self, path: str) -> bytes | None:
        """
        Return the content of the template if it exists, None otherwise

        This method is used to serve the default templates, and can be
        overridden to serve custom templates.
        """
        return self.default_templates.get(path)

    def do_GET(self):
        body = self.get_template(self.path)
        if body:
            content_type = (
                "application/javascript" if self.path.endswith(".js") else "text/html"
            )
            self.send_response(200)
            self.send_header("Content-type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()

            self.copyfile(BytesIO(body), self.wfile)
        else:
            return super().do_GET()

    def end_headers(self):
        # Enable Cross-Origin Resource Sharing (CORS)
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in self.extra_headers.items():
            self.send_header(k, v)
        if len(self.extra_headers) > 0:
            joined_headers = ",".join(self.extra_headers.keys())
            # if you don't send this, CORS blocks custom headers in javascript
            self.send_header("Access-Control-Expose-Headers", joined_headers)
        super().end_headers()


@contextlib.contextmanager
def spawn_web_server(dist_dir, extra_headers=None, handler_cls=None):
    if not extra_headers:
        extra_headers = {}
    tmp_dir = tempfile.mkdtemp()
    log_path = pathlib.Path(tmp_dir) / "http-server.log"
    q: multiprocessing.Queue[str] = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=run_web_server, args=(q, log_path, dist_dir, extra_headers, handler_cls)
    )

    try:
        p.start()
        port = q.get(timeout=20)
        hostname = "127.0.0.1"

        print(
            f"Spawning webserver at http://{hostname}:{port} "
            f"(see logs in {log_path})"
        )
        yield hostname, port, log_path
    finally:
        q.put("TERMINATE")
        p.join()
        shutil.rmtree(tmp_dir)


def run_web_server(q, log_filepath, dist_dir, extra_headers, handler_cls):
    """Start the HTTP web server

    Parameters
    ----------
    q : Queue
      communication queue
    log_path : pathlib.Path
      path to the file where to store the logs
    """

    os.chdir(dist_dir)

    log_fh = log_filepath.open("w", buffering=1)
    sys.stdout = log_fh
    sys.stderr = log_fh

    if not handler_cls:
        handler_cls = functools.partial(DefaultHandler, extra_headers=extra_headers)

    with socketserver.TCPServer(("", 0), handler_cls) as httpd:
        host, port = httpd.server_address
        print(f"Starting webserver at http://{host}:{port}")  # type: ignore[str-bytes-safe]
        httpd.server_name = "test-server"  # type: ignore[attr-defined]
        httpd.server_port = port  # type: ignore[attr-defined]
        q.put(port)

        def service_actions():
            try:
                if q.get(False) == "TERMINATE":
                    print("Stopping server...")
                    sys.exit(0)
            except queue.Empty:
                pass

        httpd.service_actions = service_actions  # type: ignore[method-assign]
        httpd.serve_forever()
