# -*- coding: utf-8 -*-
from functools import wraps


class LogHandler(object):

    HANDLERS = {}

    def __init__(self, level=None):
        self.level = level

    def log(self, level, msg):
        """Save data by registered function.
        """
        for func in self.HANDLERS.get(level, []):
            func(msg)

    def logger(self, level=None):
        """Return a decorator to register function to save data for specific
        protocol.
        """
        level = level or self.level
        assert level is not None
        if level not in self.HANDLERS:
            self.HANDLERS[level] = []

        def decorator(func):
            self.HANDLERS[level].append(func)

            @wraps(func)
            def wrapper(msg):
                func(msg)
            return wrapper
        return decorator
