#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Stub version of the urlfetch API, based on httplib."""


import sys
import gzip
import httplib
import logging
import socket
from cStringIO import StringIO
import urllib
import urlparse
import time

try:
    from namedtuple import namedtuple
except ImportError:
    from _namedtuple import namedtuple

from django.conf import settings

#MAX_RESPONSE_SIZE = 2 ** 24

MAX_REDIRECTS = 3
FETCH_DEADLINE = 25.0

REDIRECT_STATUSES = frozenset([
    httplib.MOVED_PERMANENTLY,
    httplib.FOUND,
    httplib.SEE_OTHER,
    httplib.TEMPORARY_REDIRECT,
])

_UNTRUSTED_REQUEST_HEADERS = frozenset([
    'content-length',
    'host',
    'vary',
    'via',
    'x-forwarded-for',
])


class UrlFetchError(Exception):
    pass

Response = namedtuple(
    'Response',
    'code body content_type last_modified size effective_url'
)

class Deferred:
    def __repr__(self):
        return "<deferred response>"

deferred = Deferred()

def MockResponse(body, url=None, code=200):
    return Response(code, body, 'text/plain', None, len(body), url)

class HttpClient(object):

    def _is_allowed_port(self, port):
        if port is None:
            return True
        try:
            port = int(port)
        except ValueError, e:
            return False
        if ((port >= 80 and port <= 90) or (port >= 440 and port <= 450) or port >= 1024):
            return True
        return False

    def error(self, msg, url):
        err = "%s (%s)" % (msg, url)
        logging.error(err)
        raise UrlFetchError(err)

    def fetch(self, url, payload=None, method="GET", headers=None):
        """Retrieves a URL.

        Args:
            url: String containing the URL to access.
            payload: Request payload to send, if any; None if no payload.
            method: HTTP method to use (e.g., 'GET')
        """
        if url and not url.startswith('http'):
            url = 'http://' + url
        (protocol, host, path, parameters, query, fragment) = urlparse.urlparse(url)
        if protocol and protocol[:4] != 'http':
            self.error('Invalid protocol: %s' % protocol, url)
        if not host:
            self.error('Missing host.', url)
        last_protocol = ''
        last_host = ''
        for redirect_number in xrange(MAX_REDIRECTS + 1):
            parsed = urlparse.urlparse(url)
            protocol, host, path, parameters, query, fragment = parsed

            port = urllib.splitport(urllib.splituser(host)[1])[1]

            if not self._is_allowed_port(port):
                self.error('port %s is not allowed in production!' % port, url)

            if protocol and not host:
                self.error('Missing host on redirect', url)

            if not host and not protocol:
                host = last_host
                protocol = last_protocol

            adjusted_headers = {
                    'User-Agent': settings.USER_AGENT,
                    'Host': host,
                    'Accept-Encoding': 'gzip',
            }
            if payload is not None:
                adjusted_headers['Content-Length'] = len(payload)
            if method == 'POST' and payload:
                adjusted_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            if headers:
                adjusted_headers.update(headers)

            logging.info('%s %s, payload = %s' % (method, url, bool(payload)))
            try:
                if protocol == 'http':
                    connection = httplib.HTTPConnection(host)
                elif protocol == 'https':
                    connection = httplib.HTTPSConnection(host)
                else:
                    self.error('Redirect specified invalid protocol: "%s"' % protocol, url)

                last_protocol = protocol
                last_host = host

                if query != '':
                    full_path = path + '?' + query
                else:
                    full_path = path

                orig_timeout = socket.getdefaulttimeout()
                try:
                    socket.setdefaulttimeout(FETCH_DEADLINE)
                    connection.request(method, full_path, payload, adjusted_headers)
                    http_response = connection.getresponse()
                    code = http_response.status
                    if method == 'HEAD':
                        http_response_data = ''
                    elif code != 200:
                        http_response_data = http_response.reason
                    else:
                        http_response_data = http_response.read()
                finally:
                    socket.setdefaulttimeout(orig_timeout)
                    connection.close()
            except (httplib.error, socket.error, IOError), e:
                self.error(str(e), url)

            if code in REDIRECT_STATUSES:
                url = http_response.getheader('Location', None)
                if url is None:
                    self.error('Redirecting response was missing "Location" header', url)
            else:
                if code == 200 and http_response.getheader('content-encoding') == 'gzip':
                    gzip_stream = StringIO(http_response_data)
                    gzip_file = gzip.GzipFile(fileobj=gzip_stream)
                    http_response_data = gzip_file.read()
                mime = http_response.getheader('Content-Type')
                if mime == 'application/x-tar':
                    # normalize for bitbucket/github tarballs
                    mime = 'application/octet-stream'
                size = http_response.getheader('Content-Length')
                ts = http_response.getheader('Last-Modified')
                #request = {'args': payload, 'headers': adjusted_headers}
                return Response(code, http_response_data, mime, ts, size, url)
        else:
            self.error('Too many repeated redirects', url)

_fetch = HttpClient().fetch
_async_fetch = None

try:
    import tornado
except ImportError:
    pass
else:
    try:
        import pycurl
    except ImportError:
        import tornado.simple_httpclient as _async_client
    else:
        import tornado.httpclient as _async_client
    def _async_fetch(*args, **kw):
        _async_client.AsyncHTTPClient().fetch(*args, **kw)
        return deferred

def fetch(url, callback=None, retries=0, retry_wait=5, **kw):
    i = 0
    if callback:
        if _async_fetch is None:
            raise Exception("tornado is required for asynchronous fetch")
        f = _async_fetch
        args = (url, callback)
    else:
        f = _fetch
        args = (url,)
    while True:
        try:
            return f(*args, **kw)
        except Exception:
            if i == retries:
                raise
            else:
                i += 1
                time.sleep(retry_wait)
                continue

