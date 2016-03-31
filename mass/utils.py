#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Helper functions.
"""

# built-in modules
import json

# 3rd-party modules
from botocore.client import Config

# local modules
from mass.exception import UnsupportedScheduler
from mass.input_handler import InputHandler


def submit(job, protocol=None, priority=1, scheduler='swf'):
    """Submit mass job to SWF with specific priority.
    """
    if scheduler != 'swf':
        raise UnsupportedScheduler(scheduler)
    from mass.scheduler.swf import config
    import boto3
    client = boto3.client(
        'swf',
        region_name=config.REGION,
        config=Config(connect_timeout=config.CONNECT_TIMEOUT,
                      read_timeout=config.READ_TIMEOUT))
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
                genealogy=[job.title]
            )
        }),
        executionStartToCloseTimeout=str(config.WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT),
        tagList=[job.title],
        taskStartToCloseTimeout=str(config.DECISION_TASK_START_TO_CLOSE_TIMEOUT),
        childPolicy=config.WORKFLOW_CHILD_POLICY)
    return job.title, res['runId']
