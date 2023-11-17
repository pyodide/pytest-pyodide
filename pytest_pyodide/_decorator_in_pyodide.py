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

import pickle
from base64 import b64decode, b64encode
from inspect import isclass
from io import BytesIO
from typing import Any

import pyodide_js


def pointer_to_object(ptr: int) -> Any:
    """Interpret ptr as a PyObject* and convert it to the actual Python object.

    Hopefully we got our reference counting right or this will blow up!
    """
    # This was the first way I thought of to convert a pointer into a Python
    # object: use PyObject_SetItem to assign it to a dictionary.
    # ctypes doesn't seem to have an API to do this directly.
    temp: dict[int, Any] = {}
    pyodide_js._module._PyDict_SetItem(id(temp), id(0), ptr)
    return temp[0]


class PyodideHandle:
    """See documentation for the same-name class in decorator.py

    We pickle this with persistent_id (see below) so there is no need for
    __getstate__. We pickle with persistent_id because on the other side when we
    unpickle we want to inject a selenium instance so that the reference count
    can be released by the finalizer. It seems most convenient to do that
    injection with "persistent_load".
    """

    def __init__(self, obj: Any):
        self.obj = obj
        self.ptr = id(obj)


class Pickler(pickle.Pickler):
    def persistent_id(self, obj: Any) -> Any:
        if not isinstance(obj, PyodideHandle):
            return None
        pyodide_js._module._Py_IncRef(obj.ptr)
        return ("PyodideHandle", obj.ptr)

    def reducer_override(self, obj):
        try:
            from _pytest.outcomes import OutcomeException

            if isclass(obj) and issubclass(obj, OutcomeException):
                # To shorten the repr, pytest sets the __module__ of these
                # classes to builtins. This breaks pickling. Restore the correct
                # value.
                obj.__module__ = OutcomeException.__module__
        except ImportError:
            pass
        return NotImplemented


class Unpickler(pickle.Unpickler):
    def persistent_load(self, pid: Any) -> Any:
        if not isinstance(pid, tuple) or len(pid) != 2 or pid[0] != "PyodideHandle":
            raise pickle.UnpicklingError("unsupported persistent object")
        ptr = pid[1]
        # Return the actual object rather than a PyodideHandle. In practice,
        # this is much more convenient!
        return pointer_to_object(ptr)


def encode(x: Any) -> str:
    f = BytesIO()
    p = Pickler(f)
    p.dump(x)
    return b64encode(f.getvalue()).decode()


def decode(x: str) -> Any:
    return Unpickler(BytesIO(b64decode(x))).load()


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

            def get_locals(frame):
                result = {}
                tbhide = frame.f_locals.get("__tracebackhide__")
                if tbhide:
                    result["__tracebackhide__"] = tbhide
                return result

            try:
                # works if we are using tblib >= 3.0
                pickling_support.install(get_locals=get_locals)
            except TypeError:
                # tblib < 3 or pyodide-tblib
                pickling_support.install()

        except ImportError:
            pass
        return (1, encode(e))


__all__ = ["PyodideHandle", "encode"]
