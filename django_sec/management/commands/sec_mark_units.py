from __future__ import print_function

import sys
from optparse import make_option

import django
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

from django_sec import models

def get_options(parser=None):
    make_opt = make_option
    if parser:
        make_opt = parser.add_argument
    return [
        make_opt('--name', default=None),
    ]

class Command(BaseCommand):
    help = "Links duplicate units to the true canonical unit."
    args = ''
    option_list = getattr(BaseCommand, 'option_list', ()) + tuple(get_options())
    
    def create_parser(self, prog_name, subcommand):
        """
        For ``Django>=1.10``
        Create and return the ``ArgumentParser`` which extends ``BaseCommand`` parser with
        chroniker extra args and will be used to parse the arguments to this command.
        """
        from distutils.version import StrictVersion # pylint: disable=E0611
        parser = super(Command, self).create_parser(prog_name, subcommand)
        version_threshold = StrictVersion('1.10')
        current_version = StrictVersion(django.get_version(django.VERSION))
        if current_version >= version_threshold:
            get_options(parser)
            self.add_arguments(parser)
        return parser
    
    def handle(self, **options):
        
        settings.DEBUG = False
        
        only_name = options['name']
        
        qs = models.Unit.objects.all()
        if only_name:
            qs = qs.filter(name__icontains=only_name)
        total = qs.count()
        i = 0
        dups = set()

        # Link all singular to plurals.
        qs = models.Unit.objects.filter(master=True)
        total = qs.count()
        i = 0
        for r in qs.iterator():
            i += 1
            sys.stdout.write('\r%i of %i' % (i, total))
            sys.stdout.flush()
            
            plural_qs = models.Unit.objects\
                .filter(master=True)\
                .filter(Q(name=r.name+'s')|Q(name=r.name+'es'))\
                .exclude(id=r.id)
            if plural_qs.exists():
                models.Unit.objects.filter(true_unit=r)\
                    .update(true_unit=plural_qs[0], master=False)
                r.true_unit = plural_qs[0]
                r.master = False
                r.save()

        print()       
        print('%i duplicates linked' % len(dups))
