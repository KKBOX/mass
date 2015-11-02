#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set hls is et sw=4 sts=4 ts=8:

import os
from setuptools import setup, find_packages


with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as f:
    required = f.read().splitlines()

setup(
    name='mass',
    version=':versiontools:mass:',
    description='Computer Farm Management',
    author='',
    author_email='',
    packages=find_packages(exclude=['docs', 'contrib', 'tests*']),
    include_package_data=True,
    setup_requires=[
        'versiontools >= 1.8',
    ],
    install_requires=required,
    entry_points={
        'console_scripts': [
            'mass = mass.cli:cli',
        ],
    },
)

del required
