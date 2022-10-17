"""
This file is not imported normally, it is loaded as a string and then exec'd
into a module called pytest_pyodide.decorator inside of Pyodide.

We use the name `pytest_pyodide.decorator` for this file for two reasons:

1. so that unpickling works smoothly
2. so that importing PyodideHandle works smoothly inside Pyodide

We could handle 1. by subclassing Unpickler and overriding find_class. Then we
could give a different name like `from pytest_pyodide.in_pyodide import
PyodideHandle` or something. But I think this current approach is the easiest
for users to make sense of. It is probably still quite confusing.

See also:
https://github.com/pyodide/pytest-pyodide/issues/43
"""

import ctypes
import pickle
from base64 import b64decode, b64encode
from io import BytesIO
from typing import Any


def pointer_to_object(ptr: int) -> Any:
    """Interpret ptr as a PyObject* and convert it to the actual Python object.

    Hopefully we got our reference counting right or this will blow up!
    """
    # This was the first way I thought of to convert a pointer into a Python
    # object: use PyObject_SetItem to assign it to a dictionary.
    # ctypes doesn't seem to have an API to do this directly.
    temp: dict[int, Any] = {}
    ctypes.pythonapi.PyObject_SetItem(id(temp), id(0), ptr)
    return temp[0]


class PyodideHandle:
    """See documentation for the same-name class in decorator.py

    We pickle this with persistent_id (see below) so there is no need for
    __getstate__. The only reason we pickle with persistent_id is that on the
    other side when we unpickle we want to inject a selenium instance so that
    the reference count can be released by the finalizer. It seems most
    convenient to do that injection with "persistent_load".
    """

    def __init__(self, obj: Any):
        self.obj = obj
        self.ptr = id(obj)

    def __setstate__(self, state: dict[str, Any]):
        self.ptr = state["ptr"]
        self.obj = pointer_to_object(self.ptr)


class Pickler(pickle.Pickler):
    def persistent_id(self, obj: Any) -> Any:
        if not isinstance(obj, PyodideHandle):
            return None
        ctypes.pythonapi.Py_IncRef(obj.ptr)
        return ("PyodideHandle", obj.ptr)


def encode(x: Any) -> str:
    f = BytesIO()
    p = Pickler(f)
    p.dump(x)
    return b64encode(f.getvalue()).decode()


def decode(x: str) -> Any:
    return pickle.loads(b64decode(x))


async def run_in_pyodide_main(
    mod64: str, args64: str, module_filename: str, func_name: str, async_func: bool
) -> tuple[int, str]:
    """
    This actually runs the code for run_in_pyodide.
    """
    __tracebackhide__ = True

    # We've pickled and base 64 encoded the ast module and the arguments so first
    # we have to decode them.
    mod = decode(mod64)
    args: tuple[Any] = decode(args64)

    # Compile and execute the ast
    co = compile(mod, module_filename, "exec")
    d: dict[str, Any] = {}
    exec(co, d)

    try:
        # Look up the appropriate function on the module and execute it.
        # The first None fills in the "selenium" argument.
        result = d[func_name](None, *args)
        if async_func:
            result = await result
        return (0, encode(result))
    except BaseException as e:
        try:
            # If tblib is present, we can show much better tracebacks.
            from tblib import pickling_support

            pickling_support.install()
        except ImportError:
            pass
        return (1, encode(e))


__all__ = ["PyodideHandle", "encode"]
