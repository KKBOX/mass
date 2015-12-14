#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module implements mass worker by AWS SWF.
"""

# built-in modules
from multiprocessing import Process
import json
import signal
import socket
import sys
import time
import traceback

# 3rd-party modules
import boto3

# local modules
from mass.exception import TaskError, TaskWait
from mass.scheduler.worker import BaseWorker
from mass.scheduler.swf import config
from mass.scheduler.swf.action import ActionHandler
from mass.scheduler.swf.decider import Decider


class SWFDecider(Decider):

    def run(self, task_list):
        """Poll decision task from SWF and process.
        """
        events = self.poll(task_list)
        if not events:
            return
        self.handler = ActionHandler(events)
        try:
            result = self.execute()
            if self.handler.is_waiting():
                raise TaskWait
        except TaskWait:
            self.suspend()
        except TaskError:
            _, error, _ = sys.exc_info()
            self.fail(error.reason, error.details)
        except:
            _, error, _ = sys.exc_info()
            self.fail(repr(error), json.dumps(traceback.format_exc()))
        else:
            self.complete(result)

    def execute(self):
        """Execute input of SWF workflow.
        """
        type_ = 'Job' if 'Job' in self.handler.input else 'Task'
        parallel = self.handler.input[type_].get('parallel', False)
        for child in self.handler.input[type_]['children']:
            if 'Task' in child:
                self.execute_task(child)
            elif 'Action' in child and not child['Action']['_whenerror']:
                self.execute_action(child)

            if not parallel:
                self.wait()
        if parallel:
            for child in self.handler.input[type_]['children']:
                self.wait()

    def execute_task(self, task):
        """Schedule task to SWF as child workflow and wait. If the task is not
        completed, raise TaskWait.
        """
        if self.handler.is_waiting():
            raise TaskWait
        elif self.handler.is_scheduled():
            return
        else:
            self.decisions.start_child_workflow_execution(
                workflow_id=self.handler.get_next_workflow_name(task['Task']['title']),
                workflow_type_name=config.WORKFLOW_TYPE_FOR_TASK['name'],
                workflow_type_version=config.WORKFLOW_TYPE_FOR_TASK['version'],
                task_list=config.DECISION_TASK_LIST,
                task_priority=str(self.handler.priority),
                tag_list=self.handler.tag_list + [task['Task']['title']],
                child_policy=config.WORKFLOW_CHILD_POLICY,
                control=None,
                execution_start_to_close_timeout=str(config.WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT),
                task_start_to_close_timeout=str(config.DECISION_TASK_START_TO_CLOSE_TIMEOUT),
                input=json.dumps(task))

    def execute_action(self, action):
        """Schedule action to SWF as activity task and wait. If action is not
        completed, raise TaskWait.
        """
        if self.handler.is_waiting():
            raise TaskWait
        elif self.handler.is_scheduled():
            return
        else:
            self.decisions.schedule_activity_task(
                activity_id=self.handler.get_next_activity_name(),
                activity_type_name=config.ACTIVITY_TYPE_FOR_CMD['name'],
                activity_type_version=config.ACTIVITY_TYPE_FOR_CMD['version'],
                task_list=action['Action'].get('_role', config.ACTIVITY_TASK_LIST),
                task_priority=str(self.handler.priority),
                control=None,
                heartbeat_timeout=str(60),
                schedule_to_close_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
                schedule_to_start_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
                start_to_close_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
                input=json.dumps(action))

    def fail(self, reason, details):
        try:
            type_ = 'Job' if 'Job' in self.handler.input else 'Task'
            actions = filter(lambda c: 'Action' in c, self.handler.input[type_]['children'])
            error_handlers = filter(lambda a: a['Action']['_whenerror'], actions)
            for action in error_handlers:
                self.execute_action(action)
                self.wait()
        except TaskWait:
            self.suspend()
        except TaskError:
            _, error, _ = sys.exc_info()
            super().fail(error.reason, error.details)
        except:
            _, error, _ = sys.exc_info()
            super().fail(repr(error), json.dumps(traceback.format_exc()))
        else:
            super().fail(reason, details)

    def wait(self):
        """Check if the next Task/Action could be processed. If the previous
        Task/Action is submitted to SWF, processed and successful, return
        result.
        """
        if self.decisions._data:
            raise TaskWait

        with self.handler.pop() as action:
            if not action:
                return
            elif action.status() == 'Failed':
                error = action.error()
                action.is_checked = True
                raise TaskError(error.reason, error.details)
            elif action.status() == 'TimedOut':
                raise TaskError('TimedOut')
            else:
                return action.result()


class SWFWorker(BaseWorker):

    def __init__(self, domain=None, region=None):
        super().__init__()
        self.domain = domain or config.DOMAIN
        self.region = region or config.REGION
        self.client = boto3.client('swf', region_name=self.region)
        self.decider = SWFDecider(self.domain, self.region)

    def poll(self, task_list):
        """Poll activity task of specific task list from SWF.
        """
        task = self.client.poll_for_activity_task(
            domain=self.domain,
            taskList={'name': task_list},
            identity=socket.gethostname())

        if 'taskToken' not in task:
            return None
        return task

    def run(self, task_list):
        """Poll activity task from SWF and process.
        """
        task = self.poll(task_list)
        if not task:
            return

        action = json.loads(task['input'])
        try:
            result = self.execute(action)
        except TaskError as err:
            self.client.respond_activity_task_failed(
                taskToken=task['taskToken'],
                details=err.details,
                reason=err.reason)
        except:
            _, error, _ = sys.exc_info()
            self.client.respond_activity_task_failed(
                taskToken=task['taskToken'],
                details=json.dumps(traceback.format_exc()),
                reason=repr(error))
        else:
            self.client.respond_activity_task_completed(
                taskToken=task['taskToken'],
                result=json.dumps(result))

    def start(self, farm=None):
        """Start workers for each role.

        The default number of workers for each role is 1. This setting could
        be adjusted by input farm setting.

        e.g.
        farm = {
            "shell": 3,
            "encode": 2,
            "download": 8
        }
        """
        if farm is None:
            farm = {r: 1 for r in self.role_functions.keys()}
        processes = []

        def infinite_run(func, args):
            while True:
                func(*args)
                time.sleep(5)

        def start_proc(func, args):
            p = Process(target=infinite_run, kwargs={'func': func, 'args': args})
            p.start()
            processes.append(p)

        # start decider
        decider = SWFDecider(config.DOMAIN, config.REGION)
        start_proc(decider.run, args=(config.DECISION_TASK_LIST,))

        # start worker
        for task_list, number in farm.items():
            for _ in range(number):
                worker = self.__class__(config.DOMAIN, config.REGION)
                start_proc(worker.run, args=(task_list,))

        def sig_handler(signum, frame):
            for p in processes:
                p.terminate()
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            signal.signal(signum, sig_handler)

        try:
            for p in processes:
                p.join()
        finally:
            pass
