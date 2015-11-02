#!/usr/bin/env python
# -*- coding: utf-8 -*-

# built-in modules
import json

# 3rd-party modules
from flask import Flask
from flask import render_template
from flask import request
from flask import Response
import arrow

# local modules
from mass.monitor import swf

app = Flask(__name__)


def response(status_code, data):
    return Response(json.dumps(data),
                    status=status_code,
                    mimetype='application/json')


@app.errorhandler(Exception)
def internal_server_error(err):
    return response(500, {
        'message': 'Internal Server Error',
        'details': str(err)})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/v1/<region>/<domain>/jobs', methods=['GET'])
def list_jobs(region, domain):
    oldest = request.args.get('oldest', arrow.utcnow().replace(days=-1).timestamp)
    jobs = swf.list_jobs(
        region=region,
        domain=domain,
        oldest=arrow.get(oldest).datetime)
    return response(200, jobs)


@app.route('/api/v1/<region>/<domain>/jobs/<workflow_id>', methods=['GET'])
def retrive_job(region, domain, workflow_id):
    oldest = request.args.get('oldest', arrow.utcnow().replace(days=-1).timestamp)

    jobs = swf.retrieve_jobs(
        region=region,
        domain=domain,
        workflow_id=workflow_id,
        oldest=oldest)
    for job in jobs:
        if job['executionStatus'] == 'OPEN':
            continue
        for event in swf.retrieve_job_history(
                region=region,
                domain=domain,
                workflow_id=workflow_id,
                run_id=job['execution']['runId'],
                reverse=True):
            attr_name = [k for k in event.keys() if k.endswith('Attributes')][0]
            result = event[attr_name]
            result = {k: v for k, v in result.items() if not k.startswith('decision')}
            job['executionResult'] = result
            break
    return response(200, jobs)


if __name__ == '__main__':
    app.run(debug=True)
