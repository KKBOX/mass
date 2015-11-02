#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper class for creating decision responses.
Copied from boto.swf.layer1_decisions.
"""


class Decisions:

    def __init__(self):
        self._data = []

    def schedule_activity_task(self,
                               activity_id,
                               activity_type_name,
                               activity_type_version,
                               task_list=None,
                               task_priority=None,
                               control=None,
                               heartbeat_timeout=None,
                               schedule_to_close_timeout=None,
                               schedule_to_start_timeout=None,
                               start_to_close_timeout=None,
                               input=None):
        o = {}
        o['decisionType'] = 'ScheduleActivityTask'
        attrs = o['scheduleActivityTaskDecisionAttributes'] = {}
        attrs['activityId'] = activity_id
        attrs['activityType'] = {
            'name': activity_type_name,
            'version': activity_type_version,
        }
        if task_list is not None:
            attrs['taskList'] = {'name': task_list}
        if task_priority is not None:
            attrs['taskPriority'] = task_priority
        if control is not None:
            attrs['control'] = control
        if heartbeat_timeout is not None:
            attrs['heartbeatTimeout'] = heartbeat_timeout
        if schedule_to_close_timeout is not None:
            attrs['scheduleToCloseTimeout'] = schedule_to_close_timeout
        if schedule_to_start_timeout is not None:
            attrs['scheduleToStartTimeout'] = schedule_to_start_timeout
        if start_to_close_timeout is not None:
            attrs['startToCloseTimeout'] = start_to_close_timeout
        if input is not None:
            attrs['input'] = input
        self._data.append(o)

    def start_child_workflow_execution(self,
                                       workflow_type_name,
                                       workflow_type_version,
                                       workflow_id,
                                       child_policy=None,
                                       control=None,
                                       execution_start_to_close_timeout=None,
                                       input=None,
                                       tag_list=None,
                                       task_list=None,
                                       task_priority=None,
                                       task_start_to_close_timeout=None):
        o = {}
        o['decisionType'] = 'StartChildWorkflowExecution'
        attrs = o['startChildWorkflowExecutionDecisionAttributes'] = {}
        attrs['workflowType'] = {
            'name': workflow_type_name,
            'version': workflow_type_version,
        }
        attrs['workflowId'] = workflow_id
        if child_policy is not None:
            attrs['childPolicy'] = child_policy
        if control is not None:
            attrs['control'] = control
        if execution_start_to_close_timeout is not None:
            attrs['executionStartToCloseTimeout'] = execution_start_to_close_timeout
        if input is not None:
            attrs['input'] = input
        if tag_list is not None:
            attrs['tagList'] = tag_list
        if task_list is not None:
            attrs['taskList'] = {'name': task_list}
        if task_priority is not None:
            attrs['taskPriority'] = task_priority
        if task_start_to_close_timeout is not None:
            attrs['taskStartToCloseTimeout'] = task_start_to_close_timeout
        self._data.append(o)

    def complete_workflow_execution(self, result=None):
        o = {}
        o['decisionType'] = 'CompleteWorkflowExecution'
        attrs = o['completeWorkflowExecutionDecisionAttributes'] = {}
        if result is not None:
            attrs['result'] = result
        self._data.append(o)

    def fail_workflow_execution(self, reason=None, details=None):
        o = {}
        o['decisionType'] = 'FailWorkflowExecution'
        attrs = o['failWorkflowExecutionDecisionAttributes'] = {}
        if reason is not None:
            attrs['reason'] = reason
        if details is not None:
            attrs['details'] = details
        self._data.append(o)
