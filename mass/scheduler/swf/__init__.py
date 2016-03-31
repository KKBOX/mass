#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module implements mass worker by AWS SWF.
"""

# built-in modules
from __future__ import print_function
from functools import reduce, wraps
from multiprocessing import Event, Process, Queue
import json
import signal
import socket
import sys
import time
import traceback

# 3rd-party modules
from botocore.client import Config
import boto3

# local modules
from mass.exception import TaskError, TaskWait
from mass.input_handler import InputHandler
from mass.scheduler.swf import config
from mass.scheduler.swf.decider import Decider
from mass.scheduler.swf.step import StepHandler, ChildWorkflowExecution, ActivityTask
from mass.scheduler.worker import BaseWorker


def get_priority(root, root_priority, target_index):
    def count_max_serial_children(task):
        result = None
        if 'Action' in task:
            result = 0
        elif task['Task'].get('parallel', False):
            result = max(
                [count_max_serial_children(c) + 1
                 for c in task['Task']['children']])
        else:
            result = reduce(
                lambda x, y: x + y,
                [count_max_serial_children(c) + 1
                 for c in task['Task']['children']])
        return result
    type_ = [k for k in root.keys()][0]
    is_parallel = root[type_].get('parallel', False)
    priority = None
    brothers = root[type_]['children'][:target_index]
    if is_parallel:  # parallel subtask
        priority = root_priority + 1
    elif not brothers:
        priority = root_priority + 1
    else:
        priority = reduce(
            lambda x, y: x + y,
            [count_max_serial_children(b) + 1
             for b in brothers]) + root_priority + 1
    return priority


class SWFDecider(Decider):

    def run(self, task_list):
        """Poll decision task from SWF and process.
        """
        events = self.poll(task_list)
        if not events:
            return
        self.handler = StepHandler(
            events,
            activity_max_retry=config.ACTIVITY_MAX_RETRY,
            workflow_max_retry=config.WORKFLOW_MAX_RETRY)
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
        for i, child in enumerate(self.handler.input[type_]['children']):
            priority = get_priority(self.handler.input, self.handler.priority, i)
            if 'Task' in child:
                self.execute_task(child, priority)
            elif 'Action' in child and not child['Action']['_whenerror']:
                self.execute_action(child, priority)

            if not parallel:
                self.wait()
        if parallel:
            for child in self.handler.input[type_]['children']:
                self.wait()

    def execute_task(self, task, priority):
        """Schedule task to SWF as child workflow and wait. If the task is not
        completed, raise TaskWait.
        """
        if self.handler.is_waiting():
            raise TaskWait
        elif self.handler.is_scheduled():
            return
        else:
            handler = InputHandler(self.handler.protocol)
            ChildWorkflowExecution.start(
                decisions=self.decisions,
                name=self.handler.get_next_workflow_name(task['Task']['title']),
                input_data={
                    'protocol': self.handler.protocol,
                    'body': handler.save(
                        data=task,
                        genealogy=self.handler.tag_list + [task['Task']['title']])
                },
                tag_list=self.handler.tag_list + [task['Task']['title']],
                priority=priority)

    def execute_action(self, action, priority):
        """Schedule action to SWF as activity task and wait. If action is not
        completed, raise TaskWait.
        """
        if self.handler.is_waiting():
            raise TaskWait
        elif self.handler.is_scheduled():
            return
        else:
            handler = InputHandler(self.handler.protocol)
            action_name = self.handler.get_next_activity_name()
            ActivityTask.schedule(
                self.decisions,
                name=action_name,
                input_data={
                    'protocol': self.handler.protocol,
                    'body': handler.save(
                        data=action,
                        genealogy=self.handler.tag_list + ['Action%s' % action_name])
                },
                task_list=action['Action'].get('_role', config.ACTIVITY_TASK_LIST),
                priority=priority
            )

    def fail(self, reason, details):
        try:
            type_ = 'Job' if 'Job' in self.handler.input else 'Task'
            actions = filter(lambda c: 'Action' in c, self.handler.input[type_]['children'])
            for i, child in enumerate(self.handler.input[type_]['children']):
                if 'Action' not in child:
                    continue
                if child['Action']['_whenerror'] is False:
                    continue
                priority = get_priority(self.handler.input, self.handler.priority, i)
                self.execute_action(child, priority)
                self.wait()
        except TaskWait:
            self.suspend()
        except TaskError:
            _, error, _ = sys.exc_info()
            super(SWFDecider, self).fail(
                error.reason[:config.MAX_REASON_SIZE] if error.reason else error.reason,
                error.details[:config.MAX_DETAIL_SIZE] if error.details else error.details)
        except:
            _, error, _ = sys.exc_info()
            super(SWFDecider, self).fail(
                repr(error)[:config.MAX_REASON_SIZE],
                traceback.format_exc()[:config.MAX_DETAIL_SIZE])
        else:
            super(SWFDecider, self).fail(
                reason[:config.MAX_REASON_SIZE] if reason else reason,
                details[:config.MAX_DETAIL_SIZE] if details else details)

    def wait(self):
        """Check if the next step could be processed. If the previous step
        is submitted to SWF, processed and successful, return result.
        """
        if self.decisions._data:
            raise TaskWait

        with self.handler.pop() as step:
            if not step:
                return
            if step.status() in ['Failed', 'TimedOut']:
                if step.should_retry():
                    step.retry(self.decisions)
                    raise TaskWait
                else:
                    error = step.error()
                    step.is_checked = True
                    raise TaskError(error.reason, error.details)
            else:
                return step.result()


def execute_action_proc(execute, action, event, queue):
    try:
        start_time = time.time()
        result = execute(action)
        execution_time = time.time() - start_time
        queue.put({
            'status': 'completed',
            'result': result,
            'execution_time': execution_time
        })
    except TaskError as err:
        queue.put({
            'status': 'failed',
            'reason': err.reason,
            'details': err.details
        })
    except Exception as e:
        _, exc_value, _ = sys.exc_info()
        queue.put({
            'status': 'failed',
            'reason': repr(e),
            'details': traceback.format_exc()
        })
    finally:
        event.set()


class SWFWorker(BaseWorker):

    def __init__(self, domain=None, region=None):
        super(SWFWorker, self).__init__()
        self.domain = domain or config.DOMAIN
        self.region = region or config.REGION
        self.client = boto3.client(
            'swf',
            region_name=self.region,
            config=Config(connect_timeout=config.CONNECT_TIMEOUT,
                          read_timeout=config.READ_TIMEOUT))
        self.decider = SWFDecider(self.domain, self.region)
        self.task_token = None

    def try_except(self, exception=Exception, handler=print):

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    func(*args, **kwargs)
                except exception as e:
                    handler(e)
            return wrapper
        return decorator

    def poll(self, task_list):
        """Poll activity task of specific task list from SWF.
        """
        task = self.client.poll_for_activity_task(
            domain=self.domain,
            taskList={'name': task_list},
            identity=socket.gethostname())

        if 'taskToken' not in task:
            return None
        self.task_token = task['taskToken']
        return task

    def heartbeat(self, task_token, details=''):
        return self.client.record_activity_task_heartbeat(
            taskToken=task_token,
            details=details
        )

    def execute_action(self, action):
        event = Event()
        queue = Queue()
        proc = Process(
            target=execute_action_proc,
            args=(self.execute, action, event, queue))
        proc.start()

        # Send heartbeat.
        heartbeat_retry = 0
        while not event.is_set():
            event.wait(config.ACTIVITY_HEARTBEAT_INTERVAL)
            try:
                res = self.heartbeat(self.task_token)
                if res['cancelRequested']:
                    proc.terminate()
                    proc.join()
                    return Result('cancelled', -1, '', '', '', -1)
            except Exception as err:
                if heartbeat_retry <= config.ACTIVITY_HEARTBEAT_MAX_RETRY:
                    heartbeat_retry += 1
                    continue
                else:
                    proc.terminate()
                    proc.join()
                    raise

        # Evaluate the result.
        result = queue.get_nowait()
        proc.join()
        return result

    @try_except(Exception)
    def run(self, task_list):
        """Poll activity task from SWF and process.
        """
        task = self.poll(task_list)
        if not task:
            return

        activity_input = json.loads(task['input'])
        handler = InputHandler(activity_input['protocol'])
        action = handler.load(activity_input['body'])
        result = self.execute_action(action)
        if result['status'] == 'completed':
            self.client.respond_activity_task_completed(
                taskToken=self.task_token,
                result=json.dumps(result['result'])[:config.MAX_RESULT_SIZE])
        else:
            self.client.respond_activity_task_failed(
                taskToken=self.task_token,
                details=result['details'][:config.MAX_DETAIL_SIZE],
                reason=result['reason'][:config.MAX_REASON_SIZE])

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
