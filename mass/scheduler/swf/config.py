#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The name of AWS region.
REGION = 'ap-northeast-1'

# The name of the domain in which the workflow execution is created
DOMAIN = 'mass'

# The time in seconds till a timeout exception is thrown when attempting to make a connection.
CONNECT_TIMEOUT = 50

# The time in seconds till a timeout exception is thrown when attempting to read from a connection.
READ_TIMEOUT = 70

# The maximum length of the input field that is sent to SWF.
MAX_INPUT_SIZE = 32000

# The maximum length of the result field that is sent to SWF.
MAX_RESULT_SIZE = 32000

# The maximum length of the reason field that is sent to SWF.
MAX_REASON_SIZE = 256

# The maximum length of the detail field that is sent to SWF.
MAX_DETAIL_SIZE = 32000

# The SWF workflow type for Job.
WORKFLOW_TYPE_FOR_JOB = {'name': 'Job', 'version': '0.1'}

# The SWF workflow type for Task.
WORKFLOW_TYPE_FOR_TASK = {'name': 'Task', 'version': '0.1'}

# The SWF activity type for Action.
ACTIVITY_TYPE_FOR_ACTION = {'name': 'Action', 'version': '0.1'}

# The default task list to use for the decision tasks.
DECISION_TASK_LIST = 'mass'

# The default task list to use for the activity tasks.
ACTIVITY_TASK_LIST = 'mass'

# Specifies the policy to use for the child workflow executions if parent
# workflow is terminated
WORKFLOW_CHILD_POLICY = 'TERMINATE'  # TERMINATE | REQUEST_CANCEL | ABANDON

# The timeout limit for workflow execution in second.
WORKFLOW_EXECUTION_START_TO_CLOSE_TIMEOUT = 7 * 24 * 60 * 60

# The timeout limit for decision task in second.
DECISION_TASK_START_TO_CLOSE_TIMEOUT = 60

# The timeout limit for activity task in second.
ACTIVITY_TASK_START_TO_CLOSE_TIMEOUT = 7 * 24 * 60 * 60

# The heartbeat timeout for activity task in second.
ACTIVITY_HEARTBEAT_TIMEOUT = 60 * 60

# The interval of activity heartbeat.
ACTIVITY_HEARTBEAT_INTERVAL = 15 * 60  # for 900 workers

# The max retry count of activity heartbeat.
ACTIVITY_HEARTBEAT_MAX_RETRY = 2

# The max retry count of activity task.
ACTIVITY_MAX_RETRY = 2

# The max retry count of workflow execution.
WORKFLOW_MAX_RETRY = 0
