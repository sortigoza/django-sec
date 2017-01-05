from __future__ import print_function

import os
from datetime import timedelta, date
import time
import socket
import threading
from functools import cmp_to_key
import warnings
import shutil

import six

import django
from django.core.management import call_command
from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

from django_sec import models
from django_sec import utils
from django_sec import constants as c

warnings.simplefilter('error', RuntimeWarning)

socket.gethostname = lambda: 'localhost'

class Tests(TestCase):
    
    #fixtures = ['test_jobs.json']
    
    def setUp(self):
        pass
        
    def _test_example(self):
        
        # get a file from the index. it may or may not be present on our hard disk.
        # if it's not, it will be downloaded
        # the first time we try to access it, or you can call .download() explicitly
        filing = models.Index.objects\
            .filter(form='10-K', cik=1090872)\
            .order_by('-date')[0]
        
        print(filing.name)
        
        # initialize XBRL parser and populate an attribute called fields with a dict
        # of 50 common terms
        x = filing.xbrl()
        
        print(x.fields['FiscalYear'])
        
        print(x.fields)
        
        # fetch arbitrary XBRL tags representing eiter an Instant or a Duration in time
        print('Tax rate',
            x.GetFactValue('us-gaap:EffectiveIncomeTaxRateContinuingOperations', 'Duration'))
        
        if x.loadYear(1): 
            # Most 10-Ks have two or three previous years contained in them for the major values.
            # This call switches the contexts to the prior year (set it to 2 or 3 instead of 1 to
            # go back further) and reloads the fundamental concepts.
            # Any calls to GetFactValue will use that year's value from that point on.
                            
            print(x.fields['FiscalYear'])
        
            print(x.fields)
        
            print('Tax rate',
                x.GetFactValue('us-gaap:EffectiveIncomeTaxRateContinuingOperations', 'Duration'))
    
    def test_sec_import_index_attrs(self):
        
        # Download index file.
        out = six.StringIO()
        ret = call_command(
            'sec_import_index',
            start_year='2016',#str(date.today().year-1),
            max_lines='20',
            quarter='1',
            traceback=True,
            # We have to use dryrun, and not test the actual download and process code
            # because the SEC ftp servers are too intermittent.
            dryrun=True,
            stdout=out)
        out = out.getvalue()
        print(out)
        self.assertTrue('error' not in out.lower())
        
        _fn = '/tmp/django_sec/company_2016_1.zip'
        try:
            os.remove(_fn)
        except OSError:
            pass
        self.assertTrue(not os.path.isfile(_fn))
        shutil.copy('django_sec/fixtures/company_2016_1.zip', _fn)
        self.assertTrue(os.path.isfile(_fn))
        
        # Extract attributes from all downloaded indexes.
        out = six.StringIO()
        call_command(
            'sec_import_attrs',
            start_year=str(date.today().year-1),
            verbose=True,
            traceback=True,
            stdout=out)
        out = out.getvalue()
        print(out)
        self.assertTrue('error' not in out.lower())
    
    def _test_sec_xbrl_to_csv(self):
        call_command('sec_xbrl_to_csv')
        
    def test_sec_mark_units(self):
        unit, _ = models.Unit.objects.get_or_create(name='U_iso4217USD')
        # In Django >= 1.9, you can't set a self-referential field during creation.
        unit.save()
        self.assertTrue(unit.true_unit)
        self.assertEqual(unit.true_unit, unit)
        
        call_command('sec_mark_units')
