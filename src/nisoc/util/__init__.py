
import os
from os.path import join as pathjoin, exists as pathexists, basename, dirname
from urlparse import urlparse
from urllib import quote_plus
import time

from nisoc.util.urlfetch import fetch
from nisoc import settings

def cached_fetch(url):
    netloc = urlparse(url).netloc.strip('/')
    cachedir = pathjoin(settings.DATA_CACHE_ROOT, netloc)
    cached_copy = pathjoin(cachedir, quote_plus(url))
    wget = True
    if pathexists(cached_copy):
        age = time.time() - os.stat(cached_copy).st_mtime
        if age < settings.CACHE_LIMIT:
            wget = False
    if wget:
        response = fetch(url)
        if response.code == 200:
            if not pathexists(cachedir):
                os.makedirs(cachedir)
            with open(cached_copy, 'wb') as cached:
                cached.write(response.body)
        elif response.code >= 400:
            raise IOError('%s - %s (%s)' % (response.code, url, response.body[:200]))
    assert pathexists(cached_copy), 'missing - %s' % cached_copy
    return cached_copy

