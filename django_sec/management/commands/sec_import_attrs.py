import urllib
import os
import re
import sys
from zipfile import ZipFile
import time
from datetime import date, datetime
from optparse import make_option
from StringIO import StringIO
import traceback

from django.core.management.base import NoArgsCommand, BaseCommand
from django.db import transaction, connection
from django.conf import settings
from django.utils import timezone

from django_sec import models
from django_sec.models import DATA_DIR, c

class Command(BaseCommand):
    help = "Shows data from filings."
    args = '<form>'
    option_list = BaseCommand.option_list + (
        make_option('--cik',
            default=None),
        make_option('--form',
            default='10-K'),
        make_option('--start-year',
            default=None),
        make_option('--end-year',
            default=None),
        make_option('--quarter',
            default=None),
        make_option('--dryrun',
            action='store_true',
            default=False),
        make_option('--force',
            action='store_true',
            default=False),
        make_option('--verbose',
            action='store_true',
            default=False),
    )
    
    def handle(self, **options):
        
        self.dryrun = options['dryrun']
        self.force = options['force']
        self.verbose = options['verbose']
        
        self.cik = (options['cik'] or '').strip()
        
        forms = (options['form'] or '').strip().split(',')
        
        start_year = options['start_year']
        if start_year:
            start_year = int(start_year)
        else:
            start_year = date.today().year - 1
        self.start_year = start_year
            
        end_year = options['end_year']
        if end_year:
            end_year = int(end_year)
        else:
            end_year = date.today().year
        self.end_year = end_year

        tmp_debug = settings.DEBUG
        settings.DEBUG = False
        transaction.enter_transaction_management()
        transaction.managed(True)
        try:
            for form in forms:
                print 'form:',form
                self.import_attributes(form=form)
        finally:
            settings.DEBUG = tmp_debug
            if self.dryrun:
                print 'This is a dryrun, so no changes were committed.'
                transaction.rollback()
            else:
                transaction.commit()
            transaction.leave_transaction_management()
            connection.close()
    
    def import_attributes(self, form):
        # Get a file from the index.
        # It may or may not be present on our hard disk.
        # If it's not, it will be downloaded
        # the first time we try to access it, or you can call
        # .download() explicitly.
        q = models.Index.objects.filter(
            year__in=range(self.start_year, self.end_year))
        if not self.force:
            q = q.filter(
                attributes_loaded=False,
                valid=True,
            )
        if form:
            q = q.filter(form=form)
        if self.cik:
            q = q.filter(company__cik=self.cik, company__load=True)
        total = q.count()
        i = 0
        print '%i %s indexes found.' % (total, form)
        for ifile in q.iterator():
            i += 1
            print 'Processing index %s (%i of %i)' % (ifile.filename, i, total)
            ifile.download(verbose=self.verbose)
            #print 'xbrl link:',ifile.xbrl_link()
            
            # Initialize XBRL parser and populate an attribute called fields with
            # a dict of 50 common terms.
            x = None
            error = None
            try:
                x = ifile.xbrl()
            except Exception, e:
                ferr = StringIO()
                traceback.print_exc(file=ferr)
                error = ferr.getvalue()
            
            if x is None:
                if error is None:
                    error = 'No XBRL found.'
                models.Index.objects.filter(id=ifile.id)\
                    .update(valid=False, error=error)
                continue
            
            #x.loadYear(2)
#            print'Year:', x.fields['FiscalYear']
            company = ifile.company
            max_text_len = 0
            unique_attrs = set()
            bulk_objects = []
            prior_keys = set()
            commit_freq = 100
            j = sub_total = 0
            #print
            for node, sub_total in x.iter_namespace():
                j += 1
                if not j % commit_freq:
                    print '\rImporting attribute %i of %i.' % (j, sub_total),
                    sys.stdout.flush()
                    if not self.dryrun:
                        transaction.commit()
                matches = re.findall('^\{([^\}]+)\}(.*)$', node.tag)
                if matches:
                    ns, attr_name = matches[0]
                else:
                    ns = None
                    attr_name = node
                decimals = node.attrib.get('decimals', None)
                if decimals is None:
                    continue
                if decimals.upper() == 'INF':
                    decimals = 6
                decimals = int(decimals)
                max_text_len = max(max_text_len, len((node.text or '').strip()))
                context_id = node.attrib['contextRef']
    #            if context_id != 'D2009Q4YTD':
    #                continue
                start_date = x.get_context_start_date(context_id)
                if not start_date:
                    continue
                end_date = x.get_context_end_date(context_id)
                if not end_date:
                    continue
                namespace, _ = models.Namespace.objects.get_or_create(name=ns.strip())
                attribute, _ = models.Attribute.objects.get_or_create(
                    namespace=namespace,
                    name=attr_name,
                    defaults=dict(load=True),
                )
                if not attribute.load:
                    continue
                unit, _ = models.Unit.objects.get_or_create(name=node.attrib['unitRef'].strip())
                value = node.text.strip()
                if not value:
                    continue
                #print attribute
                models.Attribute.objects.filter(id=attribute.id).update(total_values_fresh=False)
                #print context_id,attribute.name,node.attrib['decimals'],unit,start_date,end_date,ifile.date
                
                if models.AttributeValue.objects.filter(company=company, attribute=attribute, start_date=start_date).exists():
                    continue
                
                # Some attributes are listed multiple times in differently
                # named contexts even though the value and date ranges are
                # identical.
                key = (company, attribute, start_date)
                if key in prior_keys:
                    continue
                prior_keys.add(key)
                
                bulk_objects.append(models.AttributeValue(
                    company=company,
                    attribute=attribute,
                    start_date=start_date,
                    end_date=end_date,
                    value=value,
                    unit=unit,
                    filing_date=ifile.date,
                ))
                
                if not len(bulk_objects) % commit_freq:
                    models.AttributeValue.objects.bulk_create(bulk_objects)
                    bulk_objects = []
                    prior_keys.clear()
            print '\rImporting attribute %i of %i.' % (sub_total, sub_total),
            print
            
            if bulk_objects:
                models.AttributeValue.objects.bulk_create(bulk_objects)
                bulk_objects = []
                
            models.Index.objects.filter(id=ifile.id).update(attributes_loaded=True)
            
            models.Attribute.do_update()
            
            models.Unit.do_update()
            
            if not self.dryrun:
                transaction.commit()