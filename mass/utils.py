#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper functions.
"""

# built-in modules
import json

# 3rd-party modules
import boto3

# local modules
from mass.input_handler import InputHandler
from mass.scheduler.swf import config


def submit(job, protocol=None, priority=1):
    """Submit mass job to SWF with specific priority.
    """
    client = boto3.client('swf', region_name=config.REGION)
    handler = InputHandler(protocol)

    res = client.start_workflow_execution(
        domain=config.DOMAIN,
        workflowId=job.title,
        workflowType=config.WORKFLOW_TYPE_FOR_JOB,
        taskList={'name': config.DECISION_TASK_LIST},
        taskPriority=str(priority),
        input=json.dumps({
            'protocol': protocol,
            'body': handler.save(
                data=job,
                job_title=job.title,
                task_title=job.title
            )
        }),
        executionStartToCloseTimeout=str(config.WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT),
        tagList=[job.title],
        taskStartToCloseTimeout=str(config.DECISION_TASK_START_TO_CLOSE_TIMEOUT),
        childPolicy=config.WORKFLOW_CHILD_POLICY)
    return job.title, res['runId']
