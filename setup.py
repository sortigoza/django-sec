#!/usr/bin/env python
import os
import urllib

from setuptools import setup, find_packages, Command

VERSION = (0, 1, 0)
__version__ = '.'.join(map(str, VERSION))

setup(
    name = "pysec",
    version = __version__,
    packages = find_packages(),
#    package_data = {
#        'pysec': [
#            'templates/*.*',
#            'templates/*/*.*',
#            'templates/*/*/*.*',
#            'static/*.*',
#            'static/*/*.*',
#            'static/*/*/*.*',
#        ],
#    },
    author = "Luke Rosiak",
    author_email = "",
    description = "Parse XBRL filings from the SEC's EDGAR in Python",
    license = "LGPL",
    url = "https://github.com/lukerosiak/pysec",
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: LGPL License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe = False,
    install_requires = ['Django>=1.4.0', 'lxml'],
)
