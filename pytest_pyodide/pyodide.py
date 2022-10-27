class JsException(Exception):
    """
    The python code of the test can call javascript functions using
    ```
    from js import XMLHttpRequest

    xhr = XMLHttpRequest.new()
    xhr.responseType = 'arraybuffer';
    xhr.open('url', None, False)  # this will fail in main thread
    ```

    The code fails and raises a `JsException` in the pyodide environment. When the exception
    is sent back to host, the host tries to unpickle the exception. The unpickle will fail
    because "pyodide.JsException" only exists in the pyodide environment.
    """
