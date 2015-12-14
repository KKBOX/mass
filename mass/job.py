#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module provides Job, Task and Action class to generate mass job.

Example:

with Job('Job Title') as job:
    with Task('Task Title'):
        Action(cmd='sleep 10', _role='shell')
"""


class Base(dict):
    """The base object of Job, Task and Action

    "Base" maintains the parent-child relationship of Job/Task/Action by
    implementing the __enter__ and __exit__ with a private stack. Every object
    within the with statement of parent is appended as child of parent.
    """

    __stack = []

    def __init__(self, **kwargs):
        self[self.__class__.__name__] = {}
        self[self.__class__.__name__]['children'] = []
        self[self.__class__.__name__].update(kwargs)
        self._kwargs = kwargs
        if Base.__stack:
            last = Base.__stack[-1]
            last[last.__class__.__name__]['children'].append(self)

    def __str__(self):
        kwargs = ', '.join(['%s=%r' % (k, v) for k, v in self._kwargs.items()])
        inputs = []
        if kwargs:
            inputs.append(kwargs)
        return '%s(%s)' % (self.__class__.__name__, kwargs)

    def __enter__(self):
        Base.__stack.append(self)
        return self

    def __exit__(self, type, value, traceback):
        item = Base.__stack.pop()
        return item

    def __getattr__(self, name):
        return self[self.__class__.__name__][name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self[self.__class__.__name__][name] = value


class Job(Base):

    """The root node of workflow.

    Args:
        title (str): The title of a Job.
        parallel (Optional[bool]): Run sub-tasks and sub-actions parallelly
            if True. Defaults to False.
    """

    def __init__(self, title, **kwargs):
        kwargs['title'] = title
        super().__init__(**kwargs)


class Task(Base):

    """The sub-set of workflow.

    Args:
        title (str): The title of a Task.
        parallel (Optional[bool]): Run sub-tasks and sub-actions parallelly
            if True. Defaults to False.
    """

    def __init__(self, title, **kwargs):
        kwargs['title'] = title
        super().__init__(**kwargs)


class Action(Base):

    """The real work of workflow.

    Args:
        _role (Optional[str]): The role name of registered funciton to process
            input. If role is None, print inputs without any processing.
            Defaults to None.
        kwargs: The keyword arguments to be forwarded to the registered role
            function.
    """

    def __init__(self, *, _role=None, _whenerror=False, **kwargs):
        super().__init__(_role=_role, _whenerror=_whenerror, **kwargs)
        self['Action'].pop('children')
