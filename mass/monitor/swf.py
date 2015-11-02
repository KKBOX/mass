#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# built-in modules
from collections import defaultdict
from datetime import datetime

# 3rd-party modules
import arrow
import boto3

# local modules
from mass.workers.swf import config


def workflows_to_jobs(workflows):
    workflows = sorted(workflows, key=lambda w: w['startTimestamp'])
    workflows = [defaultdict(list, w) for w in workflows]
    jobs = []

    def insert(workflow, roots):
        if 'parent' not in workflow:
            jobs.append(workflow)
            return

        parent = [w for w in roots if w['execution']['runId'] == workflow['parent']['runId']]
        if parent:
            parent[0]['children'].append(workflow)
            return True
        else:
            for root in roots:
                if insert(workflow, root['children']):
                    return True
        return False

    for w in workflows:
        insert(w, jobs)
    return jobs


def datetime_to_timestamp(data):
    if isinstance(data, datetime):
        return arrow.get(data).timestamp
    elif isinstance(data, dict):
        for k, v in data.items():
            data[k] = datetime_to_timestamp(v)
        return data
    elif isinstance(data, list):
        return [datetime_to_timestamp(d) for d in data]
    else:
        return data


def list_workflow_executions(region, domain, **kwargs):
    client = boto3.client('swf', region_name=region)
    paginator = client.get_paginator('list_closed_workflow_executions')
    for res in paginator.paginate(domain=domain, **kwargs):
        for workflow in res.get('executionInfos', []):
            yield workflow
    paginator = client.get_paginator('list_open_workflow_executions')
    for res in paginator.paginate(domain=domain, **kwargs):
        for workflow in res.get('executionInfos', []):
            yield workflow


def describe_workflow_execution(region, domain, **kwargs):
    client = boto3.client('swf', region_name=region)
    res = client.describe_workflow_execution(domain=domain, **kwargs)
    return res


def get_workflow_execution_history(region, domain, **kwargs):
    client = boto3.client('swf', region_name=region)
    paginator = client.get_paginator('get_workflow_execution_history')
    for res in paginator.paginate(domain=domain, **kwargs):
        for event in res['events']:
            yield event


def list_jobs(region, domain, oldest):
    jobs = []

    for workflow in list_workflow_executions(
            region=region,
            domain=domain,
            startTimeFilter={
                'oldestDate': oldest
            },
            typeFilter=config.WORKFLOW_TYPE_FOR_JOB):

        keys = [k for k in workflow.keys()]
        for k, v in workflow.items():
            if isinstance(v, datetime):
                workflow[k] = arrow.get(v).timestamp

        jobs.append(workflow)
    return jobs


def retrieve_jobs(region, domain, workflow_id, oldest):

    roots = list_workflow_executions(
        region=region,
        domain=domain,
        executionFilter={
            'workflowId': workflow_id
        },
        startTimeFilter={
            'oldestDate': oldest
        })

    try:
        start_time = min(map(lambda r: r['startTimestamp'], roots))
    except ValueError:
        # roots are not found
        return []
    workflows = list_workflow_executions(
        region=region,
        domain=domain,
        startTimeFilter={
            'oldestDate': start_time
        },
        tagFilter={
            'tag': workflow_id
        })
    jobs = workflows_to_jobs(workflows)
    jobs = datetime_to_timestamp(jobs)
    return jobs


def retrieve_job_history(region, domain, workflow_id, run_id, reverse=False):
    for event in get_workflow_execution_history(
            region=region,
            domain=domain,
            execution={
                'workflowId': workflow_id,
                'runId': run_id
            },
            reverseOrder=reverse):
        yield datetime_to_timestamp(event)
