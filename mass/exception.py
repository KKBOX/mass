#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module defines the exceptions of MASS.
"""


class TaskWait(Exception):
    """Raised to notify that the task is in progress.
    """
    pass


class TaskError(Exception):

    """Raised while task error.
    """

    def __init__(self, reason, details=None):
        super().__init__()
        self.reason = reason
        self.details = details
