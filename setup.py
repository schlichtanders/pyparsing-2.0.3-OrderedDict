#!/usr/bin/env python

"""Setup script for the pyparsing module distribution."""
from distutils.core import setup

import sys
import os

from pyparsingOD import __version__ as pyparsing_version
    
modules = ["pyparsingOD",]

setup(# Distribution meta-data
    name = "pyparsingOD",
    version = pyparsing_version,
    description = "Python parsing module. Version using collections.OrderedDict",
    author = "Stephan Sahm",
    author_email = "Stephan.Sahm@gmx.de",
    url="https://github.com/schlichtanders/pyparsing-2.0.3-OrderedDict"
    license = "MIT License",
    py_modules = modules,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        ]
    )
