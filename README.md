Mass is a Python package that helps you build complex pipelines of batch jobs.
It handles dependency resolution, workflow management, (visualization), handling failures,
command line integration, and much more.

The purpose of Mass is to address all the plumbing typically associated with long-running batch processes.
You want to chain many tasks, automate them, and failures will happen.
These tasks can be anything, but are typically long running things like
video encoding, rendering for computer graphics, DB dump, or complex algorithm on big data.

The above is copied from [Luigi](https://github.com/spotify/luigi) by Spotify
because of the nature of laziness.

[![Build Status](https://travis-ci.org/drakeguan/mass.svg?branch=master)](https://travis-ci.org/drakeguan/mass)


# Why another pipeline tool/framework?

* We don't like to maintain a centralized server or, at least, the maintenance cost should be minimized.
* Describing your job of complicated workflow should be easy as a text file, as a job script.
* Of course, you can also write down Pythonic code snippets to represent a job. Actually, There are multiple ways to describe a job.
* Dispatching your jobs into on-premise, cloud-based or even mixed environments should be the same.
* Start your job simply and then build your complicated workflow gradually.
* Future plan. Abstract the underlying dispatching framework for other solutions, including Apache Mesos.


# How to start a job ?

Just four steps to do:

0. Initiazte AWS SWF configuration.
1. Describe your job.
2. Start some workers.
3. Submit your job.

Here is a really simple sample.
We defined a job by Python script (but you are not limited to this form).
It comprises three sub-tasks which should be invoked sequentially.
And in the 2nd task, it contains another two parallel sub-tasks.
Those two nested sub-tasks would run simultaneously.
The real actions in all those tasks are just to echo some messages to the console.


## Describe your job as a workflow
```python
#!/usr/bin/env python

import mass
from mass import Job, Task, Action

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
```

## Start some workers

Two ways to start a worker.
One way is by Python:

```python
#!/usr/bin/env python

import mass
from mass.scheduler.swf import SWFWorker

worker = SWFWorker()
worker.start()
```

The other way is through cli:

```shell
mass worker start
```

## Submit the job

There are also two ways to submit a job.

One is by Python
```python
#!/usr/bin/env python

import mass

mass.submit(a_job)
```

The other is through cli:

```shell
mass job submit -j a_job_script.json
```


# Terminologies

## Workflow

Workflow is an abstract idea of things you like to do.
Nearly all bash scripts can be treated as a workflow with sequential execution.
However, some workflows allow concurrent process within.
For example, in a workflow of daily recommendation system work,
reporting steps should be after algorithmatic processing,
but those reporting steps can run simultaneously.

## Job

To describe the abstract workflow, a DAG (directed acyclic graph) is used here.
And **Job** is the top (or root) node for that.
Most of the time, it contains several steps, called **Task**.
Those tasks would execute their own duties, called **Action**,
in some order you defined, or in parallel if you allow that.

Furthermore, when we are talking about a job, it's attribute, *title*,
is used as an identity for that.
You can put anythin into a job's title,
but it is strongly suggested to make it as distinctive and unique as possible.

## Task

**Task** is a sub-set of its parent, which could be a **Job** or a parent **Task**.
There are, at least, two important duties for a task:
1) to group part of a workflow;
2) to provide meaningful (to human beings, of course) scope and title.
With the nature of DAG, you can instruct the resolution (running) order of tasks.
Furthermore, you can indicate sub-tasks in a task to execute parallelly.

## Action

**Action** is the most fundamental unit in a workflow (or **Job**).
In a workflow, the real work is all done in actions.
In viewpoint of DAG, **Action** is the leaf node.

## Worker

A **Worker** is the program to run those actions on some machine.
It can be on your laptop, VPC instances, or even within a docker instance.
It just stays there and communicates with virtual server to digest actions.

## Role

There might be different workers in charge of different actions.
For example, workers on AWS EC2 c4.2xlarge handle computing-heavy actions;
while workers on t2.medium handle the rest.
**Role** is used to categorize workers.

There are several default roles provided.
The default one, echo, would just to print out any inputs to **Action**.
Another role, cmd, would try to run your command in a forked shell.
Some other roles could be suggested and developed as long as they are benefit to people.


# Job Description

There are several ways to describe a job. Currently, three methods are supported.


## Python Script

```python
#!/usr/bin/env python

import mass
from mass import Job, Task, Action

with Job(title="", serialsubtasks=True) as a_job:
    with Task(title="Preparing a source video"):
        Action("youtube-dl https://www.youtube.com/watch?v=BI23U7U2aUY -o storytelling.mp4")
    with Task("Transcoding"):
        with Task("Transcoding to profile #0"):
            Action("ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 128k -c:a copy -f mp4 output_0.mp4")
        with Task("Transcoding to profile #1"):
            Action("ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 250k -c:a copy -f mp4 /dev/null")
        with Task("Transcoding to profile #2, audio only"):
            Action("ffmpeg -loglevel fatal -y -i storytelling.mp4 -vn -c:a libfdk_aac -b:a 96k output_2.mp4")

mass.submit(a_job)
```

## JSON

```javascript
{
  "Job": {
    "title": "",
    "serialsubtasks": true,
    "children": [
      {
        "Task": {
          "title": "Preparing a source video",
          "children": [
            {
              "Action": {
                "input": "youtube-dl https://www.youtube.com/watch?v=BI23U7U2aUY -o storytelling.mp4"
              }
            }
          ]
        }
      },
      {
        "Task": {
          "title": "Transcoding",
          "children": [
            {
              "Task": {
                "title": "Transcoding to profile #0",
                "children": [
                  {
                    "Action": {
                      "input": "ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 128k -c:a copy -f mp4 /dev/null"
                    }
                  }
                ]
              }
            },
            {
              "Task": {
                "title": "Transcoding to profile #1",
                "children": [
                  {
                    "Action": {
                      "input": "ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 250k -c:a copy -f mp4 /dev/null"
                    }
                  }
                ]
              }
            },
            {
              "Task": {
                "title": "Transcoding to profile #2, audio only",
                "children": [
                  {
                    "Action": {
                      "input": "ffmpeg -loglevel fatal -y -i storytelling.mp4 -vn -c:a libfdk_aac -b:a 96k output_2.mp4"
                    }
                  }
                ]
              }
            }
          ]
        }
      }
    ]
  }
}
```

## Alfred Job Script (Alfscript)

Alfred job script is adopted from Pixar's Alfred (and then Tractor), a Renderfarm Management System.
This format was designed for artists to submit their rendering jobs into a render farm.
The format is actually a TCL script. Yes. It is actually a program, but it can also be treat as a data.

In this alfscript format, the terminologies are a little different.
Ths workflow is composed as Job-Task-Cmd. The last (leaf) node is called Cmd instead of Action.
It is because alfscript is designed to run commandline scripts only.

If you are curious, you can refer to https://renderman.pixar.com/resources/current/tractor/scripting.html.

```tcl
Job 
    -title {Convert a Youtube video into some videos and audios}
    -serialsubtasks 1
    -subtasks {
        Task {Preparing a source video}
            -cmds {
                Cmd {youtube-dl https://www.youtube.com/watch?v=BI23U7U2aUY -o storytelling.mp4}
            }
        Task {Transcoding} 
            -subtasks {
                Task {Transcoding to profile #0} 
                    -cmds {
                        Cmd {ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 128k -c:a copy -f mp4 output_0.mp4}
                    }
                Task {Transcoding to profile #1} 
                    -cmds {
                        Cmd {ffmpeg -loglevel fatal -y -i storytelling.mp4 -c:v libx264 -b:v 250k -c:a copy -f mp4 output_0.mp4}
                    }
                Task {Transcoding to profile #2, audio only} 
                    -cmds {
                        Cmd {ffmpeg -loglevel fatal -y -i storytelling.mp4 -vn -c:a libfdk_aac -b:a 96k output_2.mp4}
                    }
            }
    }
```



# License

   Copyright 2015 KKBOX Technologies Limited

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
