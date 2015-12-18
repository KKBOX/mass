#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set hls is ai et sw=4 sts=4 ts=8 nu ft=python:

"""Parser of SWF workflow execution history.
"""

# built-in modules
from collections import defaultdict, namedtuple
from contextlib import contextmanager
import json
import uuid

# local modules
from mass.input_handler import InputHandler
from mass.scheduler.swf import config

StepError = namedtuple('StepError', ['reason', 'details'])


class Event(object):

    """Wrapper to get value of SWF event by access class members.
    """

    def __init__(self, swf_event):
        if not isinstance(swf_event, dict):
            raise TypeError()
        self._swf_event = swf_event

    def __getattr__(self, name):
        swf_name = ''.join([s.title() for s in name.split('_')])
        swf_name = swf_name[0].lower() + swf_name[1:]

        key = [k for k in self._swf_event if 'EventAttributes' in k]
        event_attrs = self._swf_event[key[0]] if key else {}

        if swf_name in self._swf_event:
            return self._swf_event[swf_name]
        elif swf_name in event_attrs:
            return event_attrs[swf_name]
        elif swf_name in event_attrs.get('workflowExecution', {}):
            return event_attrs['workflowExecution'][swf_name]
        else:
            raise AttributeError('Attribute is not found')


class Step(object):

    """Aggregate relative events as a step, include scheduled/initialed
    event, completed event or failed event.
    """

    def __init__(self, events, max_retry_count):
        self.is_checked = False
        self._events = events
        self._max_retry_count = max_retry_count

    def created_time(self):
        init_event = self.init_event()
        if not init_event:
            return None
        return init_event.event_timestamp

    def error(self):
        events = [e for e in self._events if e.event_type.endswith('Failed')]
        if not events:
            return None
        else:
            return StepError(events[0].reason, events[0].details)

    def init_event(self):
        raise NotImplementedError

    def input(self):
        return json.loads(self.init_event().input)

    def name(self):
        raise NotImplementedError

    def priority(self):
        return int(self.init_event().task_priority)

    def result(self):
        events = [e for e in self._events if e.event_type.endswith('Completed')]
        if not events:
            return json.loads('null')
        else:
            try:
                return events[0].result
            except AttributeError:
                return json.loads('null')

    def retry(self, decisions):
        raise NotImplementedError

    def retry_count(self):
        raise NotImplementedError

    def retry_name(self):
        current_id = int(self.name().split('-')[-1])
        retry_id = current_id + self.retry_count() + 1
        return '-'.join(self.name().split('-')[:-1] + [str(retry_id)])

    def should_retry(self):
        return self.retry_count() < self._max_retry_count

    def status(self):
        return self._events[-1].event_type.replace(self.type(), '')

    def task_list(self):
        return self.init_event().task_list.get('name', None)

    def type(self):
        return self.__class__.__name__


class ActivityTask(Step):

    def init_event(self):
        events = [e for e in self._events if e.event_type.endswith('Scheduled')]
        if not events:
            events = [e for e in self._events if e.event_type == 'ScheduleActivityTaskFailed']
        return events[0] if events else None

    def name(self):
        return self.init_event().activity_id

    def retry(self, decisions):
        self.schedule(
            decisions=decisions,
            name=self.retry_name(),
            input_data=self.input(),
            task_list=self.task_list(),
            priority=self.priority())

    def retry_count(self):
        retry_count = sum(
            [1 for e in self._events if e.event_type.endswith('Scheduled')]) - 1
        return retry_count

    @classmethod
    def schedule(cls, decisions, name, input_data, task_list, priority):
        decisions.schedule_activity_task(
            activity_id=name,
            activity_type_name=config.ACTIVITY_TYPE_FOR_CMD['name'],
            activity_type_version=config.ACTIVITY_TYPE_FOR_CMD['version'],
            task_list=task_list,
            task_priority=str(priority),
            control=None,
            heartbeat_timeout=str(config.ACTIVITY_HEARTBEAT_TIMEOUT),
            schedule_to_close_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
            schedule_to_start_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
            start_to_close_timeout=str(config.ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT),
            input=json.dumps(input_data))


class ChildWorkflowExecution(Step):

    def init_event(self):
        events = [e for e in self._events if e.event_type.endswith('Initiated')]
        if not events:
            events = [e for e in self._events if e.event_type == 'StartChildWorkflowExecutionFailed']
        return events[0] if events else None

    def name(self):
        return self.init_event().workflow_id

    def retry(self, decisions):
        self.start(
            decisions=decisions,
            name=self.retry_name(),
            input_data=self.input(),
            tag_list=self.tag_list(),
            priority=self.priority())

    def retry_count(self):
        retry_count = sum(
            [1 for e in self._events if e.event_type.endswith('Initiated')]) - 1
        return retry_count

    @classmethod
    def start(cls, decisions, name, input_data, tag_list, priority):
        decisions.start_child_workflow_execution(
            workflow_id=name,
            workflow_type_name=config.WORKFLOW_TYPE_FOR_TASK['name'],
            workflow_type_version=config.WORKFLOW_TYPE_FOR_TASK['version'],
            task_list=config.DECISION_TASK_LIST,
            task_priority=str(priority),
            tag_list=tag_list,
            child_policy=config.WORKFLOW_CHILD_POLICY,
            control=None,
            execution_start_to_close_timeout=str(config.WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT),
            task_start_to_close_timeout=str(config.DECISION_TASK_START_TO_CLOSE_TIMEOUT),
            input=json.dumps(input_data))

    def tag_list(self):
        return self.init_event().tag_list


class StepHandler(object):

    """Classify events of SWF execution history to steps.
    """

    def __init__(self, events, activity_max_retry=0, workflow_max_retry=0):
        self.events = []
        self.activity_max_retry = activity_max_retry
        self.workflow_max_retry = workflow_max_retry
        self.activity_newbe_count = 0
        self.workflow_newbe_count = 0

        def get_start_event(events):
            events = map(Event, events)
            events = [e for e in events if not e.event_type.startswith('Decision')]
            return events[0]

        start_event = get_start_event(events)
        self.input = json.loads(start_event.input)
        self.tag_list = start_event.tag_list
        self.priority = int(start_event.task_priority)

        input_ = json.loads(start_event.input)
        self.protocol = input_['protocol']
        handler = InputHandler(self.protocol)
        self.input = handler.load(input_['body'])

        swf_event_groups = self.classify_events(
            events, self.activity_max_retry, self.workflow_max_retry)

        def to_event(swf_events):
            if 'ActivityTask' in swf_events[0].event_type:
                return ActivityTask(swf_events, self.activity_max_retry)
            elif 'ChildWorkflowExecution' in swf_events[0].event_type:
                return ChildWorkflowExecution(swf_events, self.workflow_max_retry)

        self.events = [
            to_event(swf_events) for swf_events in swf_event_groups.values()]
        self.events = sorted(self.events, key=lambda a: a.created_time())

    @contextmanager
    def pop(self):
        unchecked_events = [a for a in self.events if not a.is_checked]
        if unchecked_events:
            yield unchecked_events[0]
            unchecked_events[0].is_checked = True
        else:
            yield None

    def get_next_activity_name(self):
        activity_count = len(
            [a for a in self.events if a.type() == 'ActivityTask'])
        activity_count += self.activity_newbe_count
        next_id = activity_count * (self.activity_max_retry + 1)

        self.activity_newbe_count += 1
        return str(next_id)

    def get_next_workflow_name(self, prefix):
        workflow_count = len(
            [e for e in self.events if e.type() == 'ChildWorkflowExecution'])
        workflow_count += self.workflow_newbe_count
        next_id = workflow_count * (self.workflow_max_retry + 1)
        next_name = '-'.join([prefix, str(uuid.uuid1()), str(next_id)])

        self.workflow_newbe_count += 1
        return next_name

    def is_scheduled(self):
        unchecked_events = [a for a in self.events if not a.is_checked]
        return len(unchecked_events) > 0

    def is_waiting(self):
        pending_events = [
            a for a in self.events if a.is_checked and a.status() in ['Scheduled', 'Started']]
        return len(pending_events) > 0

    def classify_events(self, swf_events, activity_max_retry, workflow_max_retry):
        """Classify events to steps by event type and id.
        """
        events = map(Event, swf_events)
        events = [e for e in events if not e.event_type.startswith('Decision')]
        events = [e for e in events if not e.event_type.startswith('Workflow')]

        steps = defaultdict(list)
        for event in events:
            step_name = None
            if 'ActivityTask' in event.event_type:
                if event.event_type.endswith('Scheduled'):
                    activity_id = int(event.activity_id.split('-')[-1])
                else:
                    init_event_id = event.scheduled_event_id
                    init_event = [e for e in events if e.event_id == init_event_id][0]
                    activity_id = int(init_event.activity_id.split('-')[-1])
                activity_id = activity_id - (activity_id % (activity_max_retry + 1))
                step_name = 'activity-%d' % activity_id
            elif 'ChildWorkflowExecution' in event.event_type:
                workflow_id = int(event.workflow_id.split('-')[-1])
                workflow_id = workflow_id - (workflow_id % (workflow_max_retry + 1))
                step_name = 'workflow-%d' % workflow_id

            if step_name:
                steps[step_name].append(event)
        return steps
