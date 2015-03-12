"""
Django management command for scraping http://www.translink.co.uk timetables
"""

import sys
import os
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from nisoc.translink.scraper import scrape_translink

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write('scraping translink\n')
        destroot = os.path.join(settings.DATA_ROOT, 'dist', 'translink')
        if not os.path.exists(destroot):
            os.makedirs(destroot)
        scrape_translink(destroot)
        ret = os.system('cd %s && zip google_transit *.txt' % destroot)

