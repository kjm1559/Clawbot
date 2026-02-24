#!/usr/bin/env python3
"""
Setup script for CLAUDE
"""

import os
import sys
from setuptools import setup, find_packages

setup(
    name="claude",
    version="0.1.0",
    description="Claude Code Session Reporter & Numeric Permission Controller",
    author="Claude Code Team",
    author_email="",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'claude=claude:main',
        ],
    },
    install_requires=[
        'python-telegram-bot>=20.0',
        'jsonlines',
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    keywords='claude code telegram bot permission',
)