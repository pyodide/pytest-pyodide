"""Dummy math utilities for exercising run_in_pyodide_coverage."""


def add(a, b):
    return a + b


def multiply(a, b):
    return a * b


def factorial(n):
    if n < 0:
        raise ValueError("factorial is not defined for negative numbers")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def never_called():
    # This function is intentionally never called by the tests so that the
    # coverage report will flag it as uncovered.
    return "this line should be reported as not covered"


def unreachable():  # pragma: no cover
    # This function should never be called by the tests and is excluded
    # from coverage reporting via the pragma above.
    raise RuntimeError("this function should never run")
