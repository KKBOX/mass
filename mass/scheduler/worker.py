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


class BaseWorker:
    """Base class of mass worker.
    """

    role_functions = {}

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

    def execute(self, action):
        """Execute action by relative registered function.
        """
        role = action['Action'].get('_role', None)
        if not role:
            inputs = ', '.join(['%s=%r' % (k, v) for k, v in action['Action'].items()])
            print('Action(%s)' % inputs)
            return
        else:
            kwargs = {k: v for k, v in action['Action'].items() if not k.startswith('_')}
            try:
                return self.role_functions[role](**kwargs)
            except:
                _, error, _ = sys.exc_info()
                raise TaskError(repr(error), traceback.format_exc())

    def start(self, farm):
        """Start worker
        """
        raise NotImplementedError
