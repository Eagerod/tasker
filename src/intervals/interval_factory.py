import os
from importlib import import_module
from inspect import getmembers

from base_interval import BaseInterval


class UnsupportedIntervalException(Exception):
    pass


class IntervalDefinitionException(Exception):
    pass


class IntervalFactory(object):
    """
    Factory + caching mechanism for loading up intervals from this directory.

    NOTE: This is probably way over engineered, considering intervals only really wrap up a tiny amount of
    functionality, but it'll allow for very easy extensions if there's ever a case where non-conventional intervals
    need to be added to custom installations of tasker.
    """
    _module_cache = {}

    @classmethod
    def get(cls, interval_name):
        if interval_name in cls._module_cache:
            return cls._module_cache[interval_name]

        # Attempt to load up the file from the intervals directory containing this interval.
        expected_module_name = '.{}'.format(interval_name)
        package_name = '.'.join(__name__.split('.')[0:-1])

        try:
            module = import_module(expected_module_name, package_name)
        except ImportError as e:
            raise UnsupportedIntervalException('Unknown interval: {} ({})'.format(interval_name, e.message))

        module_contents = getmembers(
            module, lambda x: type(x) is type and issubclass(x, BaseInterval) and x != BaseInterval
        )

        if len(module_contents) != 1:
            import_path = os.path.abspath(os.path.join(os.path.dirname(__file__), interval_name))
            raise IntervalDefinitionException(
                'Interval import from {} failed with incorrect number of intervals ({})'.format(
                    import_path, module_contents
                )
            )

        cls._module_cache[interval_name] = module_contents[0][1]
        return cls._module_cache[interval_name]
