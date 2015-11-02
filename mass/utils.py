#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper functions.
"""

# built-in modules
import json

# 3rd-party modules
import boto3

# local modules
from mass.workers.swf import config


def start(job, priority=1):
    """Submit mass job to SWF with specific priority.
    """
    client = boto3.client('swf', region_name=config.REGION)

    res = client.start_workflow_execution(
        domain=config.DOMAIN,
        workflowId=job.title,
        workflowType=config.WORKFLOW_TYPE_FOR_JOB,
        taskList={'name': config.DECISION_TASK_LIST},
        taskPriority=str(priority),
        input=json.dumps(job),
        executionStartToCloseTimeout=str(config.WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT),
        tagList=[job.title],
        taskStartToCloseTimeout=str(config.DECISION_TASK_START_TO_CLOSE_TIMEOUT),
        childPolicy=config.WORKFLOW_CHILD_POLICY)
    return job.title, res['runId']
