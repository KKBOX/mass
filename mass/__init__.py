#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mass.input_handler import InputHandler
from mass.job import Job, Task, Action
from mass.log_handler import LogHandler
from mass.utils import submit
from pkg_resources import get_distribution

__version__ = get_distribution('mass').version
__all__ = [submit, Job, Task, Action, InputHandler, LogHandler]
