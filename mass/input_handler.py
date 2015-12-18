# -*- coding: utf-8 -*-
from functools import wraps
import inspect


class InputHandler:

    HANDLERS = {}

    def __init__(self, protocol=None):
        self.protocol = protocol
        self.HANDLERS.setdefault('load', {})
        self.HANDLERS.setdefault('save', {})

    def save(self, data, job_title, task_title):
        """Save data by registered function.
        """
        if not self.protocol:
            return data
        kwargs = locals()
        kwargs.pop('self')
        func = self.HANDLERS['save'][self.protocol]
        args = inspect.formatargspec(*inspect.getargspec(func))
        return func(**{k: v for k, v in kwargs.items() if k in args})

    def load(self, from_save):
        """Load data by registered function.
        """
        if not self.protocol:
            return from_save
        return self.HANDLERS['load'][self.protocol](from_save)

    def saver(self, protocol=None):
        """Return a decorator to register function to save data for specific
        protocol.
        """
        protocol = protocol or self.protocol
        assert protocol is not None

        def decorator(func):
            self.HANDLERS['save'][protocol] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
            return wrapper
        return decorator

    def loader(self, protocol=None):
        """Return a decorator to register function to load data for specific
        protocol.
        """
        protocol = protocol or self.protocol
        assert protocol is not None

        def decorator(func):
            self.HANDLERS['load'][protocol] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
            return wrapper
        return decorator
