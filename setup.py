#!/usr/bin/env python
import os
import urllib

from setuptools import setup, find_packages, Command

VERSION = (0, 2, 0)
__version__ = '.'.join(map(str, VERSION))

setup(
    name = "django-sec",
    version = __version__,
    packages = find_packages(),
#    package_data = {
#        'django_sec': [
#            'templates/*.*',
#            'templates/*/*.*',
#            'templates/*/*/*.*',
#            'static/*.*',
#            'static/*/*.*',
#            'static/*/*/*.*',
#        ],
#    },
    author = "Chris Spencer",
    author_email = "chrisspen@gmail.com",
    description = "Parse XBRL filings from the SEC's EDGAR in Python",
    license = "LGPL",
    url = "https://github.com/chrisspen/django-sec",
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
