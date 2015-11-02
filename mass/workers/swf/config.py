#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The name of AWS region.
REGION = 'ap-northeast-1'

# The name of the domain in which the workflow execution is created
DOMAIN = 'mass'

# The SWF workflow type for Job.
WORKFLOW_TYPE_FOR_JOB = {'name': 'Job', 'version': '0.1'}

# The SWF workflow type for Task.
WORKFLOW_TYPE_FOR_TASK = {'name': 'Task', 'version': '0.1'}

# The SWF activity type for Cmd.
ACTIVITY_TYPE_FOR_CMD = {'name': 'Cmd', 'version': '0.1'}

# The total duration for workflow execution.
WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT = 7 * 24 * 60 * 60

# The total duration for activity task.
ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT = 7 * 24 * 60 * 60

# The heartbeat timeout of activity task.
ACTIVITY_HEARTBEAT_TIMEOUT = 60 * 60

# Specifies the policy to use for the child workflow executions if parent
# workflow is terminated
WORKFLOW_CHILD_POLICY = 'TERMINATE'  # TERMINATE | REQUEST_CANCEL | ABANDON

# The task list to use for the decision tasks.
DECISION_TASK_LIST = 'mass'

# The default task list to use for the activity tasks.
DEFAULT_ACTIVITY_TASK_LIST = 'mass'

# Specifies the maximum duration of decision tasks.
DECISION_TASK_START_TO_CLOSE_TIMEOUT = 60
