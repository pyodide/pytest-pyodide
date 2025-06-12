import io
import pickle
from typing import Any
from zoneinfo import ZoneInfo

from hypothesis import HealthCheck, settings, strategies


def is_picklable(x: Any) -> bool:
    try:
        pickle.dumps(x)
        return True
    except Exception:
        return False


def is_equal_to_self(x: Any) -> bool:
    try:
        return bool(x == x)
    except Exception:
        return False


try:
    from exceptiongroup import ExceptionGroup
except ImportError:

    class ExceptionGroup:  # type: ignore[no-redef]
        pass


class NoHypothesisUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        # Only allow safe classes from builtins.
        if module == "hypothesis":
            raise pickle.UnpicklingError()
        return super().find_class(module, name)


def no_hypothesis(x: Any) -> bool:
    try:
        NoHypothesisUnpickler(io.BytesIO(pickle.dumps(x))).load()
        return True
    except Exception:
        return False


# Generate an object of any type
any_strategy = (
    strategies.from_type(type)
    .flatmap(strategies.from_type)
    .filter(lambda x: not isinstance(x, ZoneInfo))
    .filter(is_picklable)
    .filter(lambda x: not isinstance(x, ExceptionGroup))
    .filter(no_hypothesis)
)

any_equal_to_self_strategy = any_strategy.filter(is_equal_to_self)

std_hypothesis_settings = settings(
    deadline=6000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

strategy = (
    strategies.from_type(type)
    .flatmap(strategies.from_type)
    .filter(lambda x: not isinstance(x, ZoneInfo))
    .filter(is_picklable)
)
