#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""SWF decider to poll SWF workflow execution history and report processing
results to SWF.
"""

# built-in modules
import socket

# 3rd-party modules
import boto3

# local modules
from mass.scheduler.swf.decisions import Decisions


class Decider:

    def __init__(self, domain, region):
        self.domain = domain
        self.region = region
        self.client = boto3.client('swf', region_name=self.region)

    def poll(self, task_list):
        """Poll workflow execution history from SWF.
        """
        self.decisions = Decisions()
        paginator = self.client.get_paginator('poll_for_decision_task')
        events = []
        for res in paginator.paginate(
                domain=self.domain,
                taskList={
                    'name': task_list
                },
                identity=socket.gethostname()):
            events += res['events']
            self.task_token = res['taskToken']
        return events

    def suspend(self):
        self.client.respond_decision_task_completed(
            taskToken=self.task_token,
            decisions=self.decisions._data)

    def complete(self, result):
        """Report workflow execution completed.
        """
        self.decisions.complete_workflow_execution(result=result)
        self.client.respond_decision_task_completed(
            taskToken=self.task_token,
            decisions=self.decisions._data)

    def fail(self, reason, details):
        """Report workflow execution failed.
        """
        self.decisions.fail_workflow_execution(reason, details)
        self.client.respond_decision_task_completed(
            taskToken=self.task_token,
            decisions=self.decisions._data)
