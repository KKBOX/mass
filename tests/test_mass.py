#!/usr/bin/env python
# -*- coding: utf-8 -*-

# built-in modules
from datetime import timedelta
from multiprocessing import Process
import json
import os
import subprocess
import time

# 3rd-party modules
from sh import aws
import arrow
import boto3
import pytest

# local modules
from mass import Job, Task, Action, InputHandler
from mass.scheduler.swf import config
from mass.scheduler.swf import SWFWorker
import mass


input_handler = InputHandler()


@input_handler.saver('local')
def save_to_local(data, job_title, task_title):
    file_path = '/tmp/Job_%s_Task_%s_%d.job' % (job_title, task_title, time.time())
    with open(file_path, 'w') as f:
        f.write(json.dumps(data))
    return file_path


@input_handler.loader('local')
def load_from_local(file_path):
    with open(file_path) as fp:
        return json.load(fp)


@pytest.fixture(scope='session')
def worker(request):
    worker = SWFWorker()

    @worker.role('echo')
    def echo(msg):
        output = subprocess.check_output('echo %s' % msg, shell=True)
        print(output)

    @worker.role('shell')
    def run(cmd):
        output = subprocess.check_output(cmd, shell=True)
        print(output)
    p = Process(target=worker.start, kwargs={'farm': {'echo': 1, 'shell': 2}})
    p.start()

    def fin():
        p.terminate()
        p.join()
    request.addfinalizer(fin)
    return p


@pytest.yield_fixture
def submit_job(monkeypatch):

    def submitter(job):
        workflow_id, run_id = mass.submit(job, 'local')
        monkeypatch.setenv('TEST_WORKFLOW_ID', workflow_id)
        monkeypatch.setenv('TEST_RUN_ID', run_id)
        return workflow_id, run_id
    yield submitter

    # terminate workflow if not done.
    workflow_id = os.environ.get('TEST_WORKFLOW_ID', None)
    run_id = os.environ.get('TEST_RUN_ID', None)
    if not workflow_id or not run_id:
        return
    if not is_job_done(workflow_id, run_id):
        aws.swf('terminate-workflow-execution',
                '--workflow-id', workflow_id,
                '--run-id', run_id,
                '--child-policy', 'TERMINATE',
                reason='TEST FINISHED',
                region=config.REGION,
                domain=config.DOMAIN)
    monkeypatch.delenv('TEST_WORKFLOW_ID')
    monkeypatch.delenv('TEST_RUN_ID')


def iter_workflow_execution_history(workflow_id, run_id, reverse_order=False, ignore_decision_task=True):
    client = boto3.client('swf', region_name=config.REGION)
    paginator = client.get_paginator('get_workflow_execution_history')
    for res in paginator.paginate(
        domain=config.DOMAIN,
        execution={
            'workflowId': workflow_id,
            'runId': run_id
        },
        reverseOrder=reverse_order
    ):
        for event in res['events']:
            if ignore_decision_task and event['eventType'].startswith('DecisionTask'):
                continue
            yield event


def get_execution_info(workflow_id, run_id):
    lines = aws.swf('describe-workflow-execution',
                    '--execution', 'workflowId=%s,runId=%s' % (workflow_id, run_id),
                    region=config.REGION,
                    domain=config.DOMAIN)
    info = json.loads(''.join([l for l in lines]))
    return info


def is_job_done(workflow_id, run_id):
    info = get_execution_info(workflow_id, run_id)
    return info['executionInfo']['executionStatus'] == 'CLOSED'


def get_close_status(workflow_id, run_id):
    info = get_execution_info(workflow_id, run_id)
    if info['executionInfo']['executionStatus'] != 'CLOSED':
        return None
    else:
        return info['executionInfo']['closeStatus']


def test_start_job(worker, submit_job):
    with Job('Job') as job:
        with Task('Task'):
            Action(msg='Action here at $(date).', _role='echo')

    workflow_id, run_id = submit_job(job)

    while not is_job_done(workflow_id, run_id):
        print('wait')
        time.sleep(3)
    assert get_close_status(workflow_id, run_id) == 'COMPLETED'


def test_unexpected_keywork_arguments_of_action(worker, submit_job):
    with Job('Job') as job:
        with Task('Task'):
            Action(wrong_input='Action here at $(date).', _role='echo')

    workflow_id, run_id = submit_job(job)

    while not is_job_done(workflow_id, run_id):
        print('wait')
        time.sleep(3)
    assert get_close_status(workflow_id, run_id) == 'FAILED'
    for event in iter_workflow_execution_history(workflow_id, run_id, reverse_order=True):
        assert event['eventType'] == 'WorkflowExecutionFailed'
        attr = event['workflowExecutionFailedEventAttributes']
        assert 'got an unexpected keyword argument' in attr['reason']
        break


def test_parallel_tasks(worker, submit_job):
    with Job('Job', parallel=True) as job:
        with Task('Task1'):
            Action(cmd='sleep 10', _role='shell')
        with Task('Task2'):
            Action(cmd='sleep 8', _role='shell')

    workflow_id, run_id = submit_job(job)

    while not is_job_done(workflow_id, run_id):
        print('wait')
        time.sleep(3)
    assert get_close_status(workflow_id, run_id) == 'COMPLETED'

    # check status of child workflows
    completed_child_workflows = set()
    for event in iter_workflow_execution_history(workflow_id, run_id):
        if event['eventType'] != 'ChildWorkflowExecutionStarted':
            continue
        attr = event['childWorkflowExecutionStartedEventAttributes']
        wid = attr['workflowExecution']['workflowId']
        rid = attr['workflowExecution']['runId']
        assert get_close_status(wid, rid) == 'COMPLETED'
        completed_child_workflows.add('-'.join(wid.split('-')[:-6]))
    assert completed_child_workflows == set(['Task1', 'Task2'])

    # check start time of child workflows
    completed_child_workflows = []
    start_time = {}
    for event in iter_workflow_execution_history(workflow_id, run_id):
        if event['eventType'] != 'ChildWorkflowExecutionStarted':
            continue
        attr = event['childWorkflowExecutionStartedEventAttributes']
        wid = attr['workflowExecution']['workflowId']
        task = '-'.join(wid.split('-')[:-6])
        start_time[task] = arrow.get(event['eventTimestamp'])
    assert abs(start_time['Task1'] - start_time['Task2']) < timedelta(seconds=5)


def test_handle_task_error(worker, submit_job):
    with Job('Job') as job:
        with Task(title='Task'):
            Action(cmd='fakecmd', _role='shell')
            Action(cmd='echo "an error occurred"', _role='shell', _whenerror=True)

    workflow_id, run_id = submit_job(job)

    while not is_job_done(workflow_id, run_id):
        print('wait')
        time.sleep(3)
    assert get_close_status(workflow_id, run_id) == 'FAILED'
