import os
import sys

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext, ugettext_lazy as _

from django_sec import xbrl

import constants as c
from settings import DATA_DIR

class Namespace(models.Model):
    """
    Represents an XBRL namespace used to segment attribute names.
    """
    
    name = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        db_index=True,
        unique=True)
    
    def __unicode__(self):
        return self.name

class Unit(models.Model):
    """
    Represents a numeric unit.
    """
    
    name = models.CharField(
        max_length=200,
        blank=False,
        null=False,
        db_index=True,
        unique=True)
    
    true_unit = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=_('''Points the the unit record this record duplicates.
            Points to itself if this is the master unit.'''))
    
    master = models.BooleanField(
        default=True,
        editable=False,
        help_text=_('If true, indicates this unit is the master referred to by duplicates.'))
    
    def __unicode__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.id:
            self.true_unit = self.true_unit or self
            self.master = self == self.true_unit
        super(Unit, self).save(*args, **kwargs)
    
    @classmethod
    def do_update(cls, *args, **kwargs):
        q = cls.objects.filter(true_unit__isnull=True)
        for r in q.iterator():
            r.save()

class Attribute(models.Model):
    """
    Represents a financial attribute tag.
    """
    
    namespace = models.ForeignKey('Namespace')
    
    name = models.CharField(
        max_length=500,
        blank=False,
        null=False,
        db_index=True)
    
    load = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_('If checked, all values will be loaded for this attribute.'))
    
    total_values = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=True)
    
    total_values_fresh = models.BooleanField(
        default=False,
        verbose_name='fresh')
    
    class Meta:
        unique_together = (
            ('namespace', 'name'),
        )
        index_together = (
            ('namespace', 'name'),
        )
    
    def __unicode__(self):
        return '{%s}%s' % (self.namespace, self.name)
    
    @classmethod
    def do_update(cls, *args, **kwargs):
        q = cls.objects.filter(total_values_fresh=False).only('id', 'name')
        total = q.count()
        i = 0
        for r in q.iterator():
            i += 1
            if not i % 100:
                print '\rRefreshing attribute %i of %i.' % (i, total),
                sys.stdout.flush()
            total_values = AttributeValue.objects.filter(attribute__name=r.name).count()
            cls.objects.filter(id=r.id).update(
                #total_values=r.values.all().count(),
                total_values=total_values,
                total_values_fresh=True)
        print '\rRefreshing attribute %i of %i.' % (total, total),

class AttributeValue(models.Model):
    
    company = models.ForeignKey('Company', related_name='attributes')
    
    attribute = models.ForeignKey('Attribute', related_name='values')
    
    # Inspecting several XBRL samples, no digits above 12 characters
    # or decimals above 5 were found, so I've started there and added
    # a little more to handle future increases.
    value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=False,
        null=False)
    
    unit = models.ForeignKey('Unit')
    
    start_date = models.DateField(
        blank=False,
        null=False,
        db_index=True,
        help_text=_('''If attribute implies a duration, this is the date
            the duration begins. If the attribute implies an instance, this
            is the exact date it applies to.'''))
    
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('''If this attribute implies a duration, this is the date
            the duration ends.'''))
    
    filing_date = models.DateField(
        blank=False,
        null=False,
        help_text=_('The date this information became publically available.'))
    
    class Meta:
        ordering = ('-attribute__total_values', '-start_date', 'attribute__name')
        unique_together = (
            ('company', 'attribute', 'start_date', 'end_date'),
        )
        index_together = (
            ('company', 'attribute', 'start_date'),
        )
        
    def __unicode__(self):
        return '%s %s=%s %s on %s' % (
            self.company,
            self.attribute.name,
            self.value,
            self.unit,
            self.start_date,
        )

class IndexFile(models.Model):
    
    year = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    quarter = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    filename = models.CharField(max_length=200, blank=False, null=False)
    
    total_rows = models.PositiveIntegerField(blank=True, null=True)
    
    processed_rows = models.PositiveIntegerField(blank=True, null=True)
    
    downloaded = models.DateTimeField(blank=True, null=True)
    
    processed = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ('year', 'quarter')
        unique_together = (
            ('year', 'quarter'),
        )

class Company(models.Model):

    cik = models.IntegerField(
        db_index=True,
        primary_key=True,
        help_text=_('Central index key that uniquely identifies a filing entity.'))
    
    name = models.CharField(
        max_length=100,
        db_index=True,
        blank=False,
        null=False,
        help_text=_('The name of the company.'))
    
    load = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_('If checked, all values for load-enabled attributes will be loaded for this company.'))
    
    class Meta:
        verbose_name_plural = _('companies')
    
    def __unicode__(self):
        return self.name
    
class Index(models.Model):
    
    company = models.ForeignKey(
        'Company',
        related_name='filings')
    
    form = models.CharField(
        max_length=10,
        blank=True,
        db_index=True,
        verbose_name=_('form type'),
        help_text=_('The type of form the document is classified as.'))
    
    date = models.DateField(
        blank=False,
        null=False,
        db_index=True,
        verbose_name=_('date filed'),
        help_text=_('The date the item was filed with the SEC.'))
    
    filename = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        db_index=True,
        help_text=_('The name of the associated financial filing.'))
    
    year = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    quarter = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    attributes_loaded = models.BooleanField(default=False, db_index=True)
    
    valid = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_('If false, errors were encountered trying to parse the associated files.'))
    
    error = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = _('indexes')
        unique_together = (
            # Note, filenames are not necessarily unique.
            # Filenames may be listed more than once under a different
            # form type.
            ('company', 'form', 'date', 'filename', 'year', 'quarter'),
        )
        index_together = (
            ('year', 'quarter'),
        )
    
    def xbrl_link(self):
        if self.form.startswith('10-K') or self.form.startswith('10-Q'):
            id = self.filename.split('/')[-1][:-4]
            return 'http://www.sec.gov/Archives/edgar/data/%s/%s/%s-xbrl.zip' % (self.company.cik, id.replace('-',''), id)
        return None
        
    def html_link(self):
        return 'http://www.sec.gov/Archives/%s' % self.filename

    def index_link(self):
        id = self.filename.split('/')[-1][:-4]
        return 'http://www.sec.gov/Archives/edgar/data/%s/%s/%s-index.htm' % (self.company.cik, id.replace('-',''), id)
        
    def txt(self):
        return self.filename.split('/')[-1]
        
    def localfile(self):
        filename = '%s/%s/%s/%s' % (DATA_DIR, self.company.cik,self.txt()[:-4],self.txt())
        if os.path.exists(filename):
            return filename
        return None
        
    def localpath(self):
        return '%s/%s/%s/' % (DATA_DIR, self.company.cik, self.txt()[:-4])

    def localcik(self):
        return '%s/%s/' % (DATA_DIR, self.company.cik)
    
    def html(self):
        filename = self.localfile()
        if not filename: 
            return None
        f = open(filename,'r').read()
        f_lower = f.lower()
        try:
            return f[f_lower.find('<html>'):f_lower.find('</html>')+4]
        except:
            print 'html tag not found'
            return f

    def download(self, verbose=False):
        try: 
            os.mkdir(self.localcik())
        except:
            pass
        try:
            os.mkdir(self.localpath())
        except:
            pass
        os.chdir(self.localpath())
        
        html_link = self.html_link()
        xbrl_link = self.xbrl_link()
        if verbose:
            print 'html_link:',
            print 'xbrl_link:',xbrl_link
            
        if not os.path.exists(html_link.split('/')[-1]):
            os.system('wget %s' % html_link)
        
        if xbrl_link:
            if not os.path.exists(xbrl_link.split('/')[-1]):
                os.system('wget %s' % xbrl_link)
                os.system('unzip *.zip')

    def xbrl_localpath(self):
        try:
            os.chdir(self.localpath())
        except:
            self.download()
        files = os.listdir('.')
        xml = sorted([elem for elem in files if elem.endswith('.xml')],key=len)
        if not len(xml):
            return None
        return self.localpath() + xml[0]

    def xbrl(self):
        filepath = self.xbrl_localpath()
        print 'filepath:',filepath
        if not filepath:
            print 'no xbrl found. this option is for 10-ks.'
            return
        x = xbrl.XBRL(filepath)
        x.fields['FiscalPeriod'] = x.fields['DocumentFiscalPeriodFocus']
        x.fields['FiscalYear'] = x.fields['DocumentFiscalYearFocus']
        x.fields['DocumentPeriodEndDate'] = x.fields['BalanceSheetDate']
        x.fields['PeriodStartDate'] = x.fields['IncomeStatementPeriodYTD']
        x.fields['SECFilingPage'] = self.index_link()
        x.fields['LinkToXBRLInstance'] = self.xbrl_link() 

        return x
        
    def ticker(self): #get a company's stock ticker from an XML filing
        filepath = self.xbrl_localpath()
        if filepath:
            return filepath.split('-')[0]
        return None
