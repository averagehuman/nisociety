
import os
import sys
from os.path import join as pathjoin, exists as pathexists, dirname, abspath
from itertools import groupby, izip, count

from lxml.html import parse, tostring
from nisoc.util import cached_fetch
from nisoc.translink import const as c
from nisoc.translink.reshape import (
    get_raw_csv_writer, reshape,
    TRIPDATAJOINER, TRIPDATAPARTJOINER,
)

def strip(s):
    return (' '.join(s.split('&nbsp;'))).strip()

def valid_metro_route_url(url):
    return url.startswith('/Metro/Metro-Timetables/Metro-') and url.endswith('bound/')

def scrape_translink(destroot=None):
    destroot = destroot or os.getcwd()
    rawcsvfile = pathjoin(destroot, 'translinkni-raw.csv')
    with open(rawcsvfile, 'wb') as csvfile:
        csv_writer = get_raw_csv_writer(csvfile)
        scrape_translink_metro(csv_writer)
    with open(rawcsvfile, 'rb') as csvfile:
        reshape(csvfile, destroot)
    #os.remove(rawcsvfile)

def scrape_translink_metro(writer):
    route_urls = set()
    for index_url in c.TRANSLINK_METRO_INDEX_URLS:
        try:
            html = parse(cached_fetch(index_url)).getroot()
        except IOError:
            continue
        for link in html.iterlinks():
            url = link[2]
            if valid_metro_route_url(url):
                route_urls.add(c.TRANSLINK_URL + url)
    for url in route_urls:
        for obj in iter_scrape_route(url):
            writer.writerow(obj)

def iter_scrape_route(url):
    html = parse(cached_fetch(url)).getroot()
    body = html.find('.//div[@id="MainBody"]')
    srvname = strip(html.find('.//div[@id="ltw"]').text)
    srvno = srvname.split()[-1]
    direction = url[url.rfind('-')+1:].rstrip('/').title()
    try:
        direction_id = c.DIRECTIONCODES[direction.lower()]
    except KeyError:
        direction_id = None
    srvname = '%s (%s)' % (srvname, direction)
    route = body.find('.//div[@class="lower_timetables_details_top_title"]').text
    route_parts = route.split('-')
    srvid = '%s-%s' % (c.METRO_ID, srvno.lower())
    if direction_id is not None:
        route_id = '%s-%s' % (srvid, direction.lower())
    else:
        route_id = srvid
    route_info = {
        'agency_id': c.TRANSLINK_ID,
        'service_id': srvid,
        'route_id': route_id,
        'route_url': url,
        'route_type': c.BUSROUTETYPE,
        'route_long_name': srvname,
        'route_short_name': srvno,
        'route_begin': strip(route_parts[0]),
        'route_end': strip(route_parts[-1]),
        'route_direction': direction_id,
    }
    #print srvno
    #print srvname
    container = body.find('.//div[@id="timetableContainer"]')
    tables = container.findall('table')
    def iter_tables():
        tripidx = count(1)
        stop_sequence = []
        for i, table in enumerate(tables):
            # every other table is a timetable TODO - verify
            if i % 2:
                rows = iter(table.findall('tr'))
                service_nos = timeframes = None
                for r in rows:
                    label = strip(r[0].text)
                    if label == 'Service:':
                        service_nos = [strip(td.text) for td in r[1:]]
                    elif label == 'Days of operation:':
                        timeframes = [strip(td.text) for td in r[1:]]
                        break
                assert len(service_nos) == len(timeframes)
                tripids = [str(tripidx.next()) for x in service_nos]
                datarows = []
                for row in rows:
                    # ignore rows that aren't stop time rows
                    label = strip(row[0].text)
                    if label and label[-1] != ':':
                        datarows.append((label, row))
                for i, (stop, r) in enumerate(datarows):
                    if i < len(stop_sequence):
                        # we must have the same stops in each table
                        assert stop_sequence[i] == stop, "inconsistent stop sequence between tables - %s" % stop
                    else:
                        # first time round
                        stop_sequence.append(stop)
                    times = [strip(td.text) for td in r[1:]]
                    times = [TRIPDATAPARTJOINER.join(t) for t in izip(tripids, service_nos, timeframes, times)]
                    for t in times:
                        assert t.count(TRIPDATAPARTJOINER) == 3, "found meta character in timetable data"
                    yield i, stop, times
    sortkey = lambda X: (X[0], X[1])
    stop_times = sorted(iter_tables(), key=sortkey)
    for key, group in groupby(stop_times, key=sortkey):
        info = dict(route_info)
        alltimes = []
        for item in group:
            alltimes.extend(item[2])
        info['stop_sequence'], info['stop_name'] = key
        info['schedule'] = TRIPDATAJOINER.join(alltimes)
        yield info


