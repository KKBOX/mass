#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set hls is ai et sw=4 sts=4 ts=8 nu ft=python:

# built-in modules

# 3rd-party modules
import click

# local modules
from mass.monitor.app import app
from mass.scheduler.swf import utils
from mass.scheduler.swf import SWFWorker


@click.group()
def cli():
    pass


@cli.command()
def init():
    utils.register_domain()
    utils.register_workflow_type()
    utils.register_activity_type()


@cli.group()
def worker():
    pass


@cli.group()
def job():
    pass


@cli.group()
def monitor():
    pass


@worker.command('start')
def worker_start():
    worker = SWFWorker()
    worker.start()


@job.command('submit')
@click.option('-j', '--json', help='Job Description in JSON.')
@click.option('-a', '--alfscript', help='Job Description in alfscript.')
def job_submit(json_script, alf_script):
    pass


@monitor.command('start')
def monitor_start():
    monitor = app.run(debug=True)

cli.add_command(init)
cli.add_command(worker)
cli.add_command(job)
cli.add_command(monitor)
