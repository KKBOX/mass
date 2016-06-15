#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module define base class of mass worker.
"""

# built-in modules
from functools import wraps
import sys
import traceback

# local modules
from mass.exception import TaskError


class BaseWorker(object):
    """Base class of mass worker.
    """

    role_functions = {}
    handler_functions = {}

    def role(self, name):
        """Registers a role to execute relative action.
        """
        def decorator(func):
            self.role_functions[name] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
            return wrapper
        return decorator

    def handle(self, exception):
        """Registers a error handler for specific exception.

        The inputs of handler function:
        * etype, value, tb: from sys.exc_info()
        * role: role name
        * func: role function
        * kwargs: input of role function

        Example:

        @worker.handle(Exception)
        def handler(etype, value, tb, role, func, kwargs):
            format_exc = ''.join(traceback.format_exception(etype, value, tb, limit=None))
            print(format_exc)
        """
        def decorator(func):
            self.handler_functions[exception] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
            return wrapper
        return decorator

    def execute(self, action):
        """Execute action by relative registered function.
        """
        role = action['Action'].get('_role', None)
        if not role:
            inputs = ', '.join(['%s=%r' % (k, v) for k, v in action['Action'].items()])
            print('Action(%s)' % inputs)
            return

        kwargs = {k: v for k, v in action['Action'].items() if not k.startswith('_')}
        try:
            return self.role_functions[role](**kwargs)
        except Exception:
            etype, value, tb = sys.exc_info()
            for exception, handler_function in self.handler_functions.items():
                if issubclass(value.__class__, exception):
                    try:
                        handler_function(etype, value, tb, role, self.role_functions[role], kwargs)
                    except Exception:
                        etype, value, tb = sys.exc_info()
                        raise TaskError(repr(value), traceback.format_exc())
            raise TaskError(repr(value), traceback.format_exc())

    def start(self, farm):
        """Start worker
        """
        raise NotImplementedError
