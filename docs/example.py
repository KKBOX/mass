#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# local modules
import mass
from mass import Job, Task, Action
from mass.scheduler.swf import SWFWorker

with Job("Echo Job") as a_job:
    with Task("Task #1"):
        Action("[Task #1] Let's initiate something here first.")
    with Task("Task #2", parallel=True):
        with Task("Task #2.1"):
            Action("[Task #2.1] Do something here. $(sleep)")
            Action("[Task #2.1] Another action here at $(date).")
        with Task("Task #2.2"):
            Action("[Task #2.2] Do something here. $(sleep)")
            Action("[Task #2.2] Another action here at $(date).")
    with Task("Task #3"):
        Action("All is done!")

mass.start(a_job)
worker = SWFWorker.start()
