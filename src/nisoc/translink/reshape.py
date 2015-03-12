#!/usr/bin/env python
"""
reshape flat data file to Google Transit Feed Specification (GTFS)

Incoming format
===============

A CSV file with the following fields::

        'agency_id',
        'service_id',
        'route_id',
        'route_short_name',
        'route_long_name',
        'route_url',
        'route_begin',
        'route_end',
        'route_type',
        'route_direction',
        'stop_sequence',
        'stop_name',
        'schedule',

schedule
--------

TODO - explain schedule


GTFS Format
===========

`*` - required field
`!` - additional, non-GTFS field

agency.txt
------------

    + agency_id
    + agency_name *
    + agency_url *
    + agency_timezone *
    + agency_lang
    + agency_phone
    + agency_fare_url

stops.txt
---------

    + stop_id *
    + stop_code
    + stop_name *
    + stop_desc
    + stop_lat *
    + stop_lon *
    + zone_id
    + stop_url
    + location_type
    + parent_station
    + stop_timezone

routes.txt
----------

    + route_id *
    + agency_id
    + route_short_name *
    + route_long_name *
    + route_desc
    + route_type *
    + route_url
    + route_color
    + route_text_color

trips.txt
---------

    + route_id *
    + service_id *
    + trip_id *
    + trip_headsign
    + trip_short_name
    + direction_id
    + block_id
    + shape_id
    + timeframe_id !
    + trip_sequence !

stop_times.txt
--------------

    + trip_id *
    + arrival_time *
    + departure_time *
    + stop_id *
    + stop_sequence *
    + stop_headsign
    + pickup_type
    + drop_off_type
    + shape_dist_travelled

calendar.txt
------------

    + service_id *
    + monday *
    + tuesday *
    + wednesday *
    + thursday *
    + friday *
    + saturday *
    + sunday *
    + start_date *
    + end_date *

"""

from __future__ import with_statement
import sys
import os
import csv
from itertools import groupby
from os.path import join as pathjoin, exists as pathexists, dirname, abspath
import shutil

from django.template.defaultfilters import slugify
from django.conf import settings

from nisoc.translink.dateutil import get_time_period_name_and_weight, split_timeframe, daycode_to_name
from nisoc.translink import const as c

TRIPDATAJOINER = '!!'
TRIPDATAPARTJOINER = '#'
#the incoming csv file should have the following columns
RAW_CSV_FIELDS = [
        'agency_id',
        'service_id',
        'route_id',
        'route_short_name',
        'route_long_name',
        'route_url',
        'route_begin',
        'route_end',
        'route_type',
        'route_direction',
        'stop_sequence',
        'stop_name',
        'schedule',
]
#the files to be created and their respective columns.
OUTFILESANDFIELDS = (
    ('agency', '''agency_id agency_name agency_url agency_timezone agency_lang
                    agency_phone agency_fare_url'''),
    ('stops_as_scraped', '''stop_id stop_code stop_name stop_desc stop_lat stop_lon
                zone_id stop_url location_type parent_station stop_timezone'''),
    ('routes', '''route_id agency_id route_short_name route_long_name
                route_desc route_type route_url route_color route_text_color'''),
    ('routestops', 'route_id stop_sequence stop_id direction'),
    ('trips',  '''route_id service_id trip_id trip_headsign
                trip_short_name direction_id block_id shape_id timeframe_id trip_sequence'''),
    ('stop_times', '''trip_id arrival_time departure_time stop_id
                    stop_sequence stop_headsign pickup_type drop_off_type
                    shape_dist_travelled'''),
    ('calendar', '''service_id monday tuesday wednesday thursday friday saturday sunday
                    start_date end_date'''),
)
DEFAULT_LATT = 54.5971852032
DEFAULT_LONG = -5.934116323
STATIONS = []


def get_raw_csv_writer(fp):
    return csv.DictWriter(fp, RAW_CSV_FIELDS)

def get_raw_csv_reader(fp):
    return csv.DictReader(fp, RAW_CSV_FIELDS)

def make_id(*args):
    return slugify(' '.join(args))

def make_route_id(*args):
    return make_id(*args).replace('-', '').upper()

def make_trip_id(routeid, timeframeid, tripno):
    return make_id(routeid, timeframeid, '%03d' % int(tripno))

def write_agency(destroot):
    outfile = os.path.join(destroot, 'agency.txt')
    fields = dict(
        agency_id='translinkni',
        agency_name='Translink N.I.',
        agency_url='http://www.translink.co.uk',
        agency_timezone='Europe/London',
        agency_lang='en',
        agency_phone='',
        agency_fare_url='',
    )
    with open(outfile, 'wb') as fp:
        fieldnames = OUTFILESANDFIELDS[0][1].split()
        writer = csv.DictWriter(fp, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerow(fields)

def write_stops(reader, writer):
    """
    Write unique stop names per-direction
    """
    data = set((row['agency_id'], row['route_short_name'], row['stop_name'], row['route_direction']) for row in reader)
    for agencyid, route, stopname, direction in sorted(data):
        #print agencyid, stopname, direction
        stoptype = 0
        #stopid = make_id(groupid, stopname)
        stopid = make_id(agencyid, stopname, direction)
        row = [route, stopid, None, stopname, None, DEFAULT_LONG,
                DEFAULT_LATT, None, None, stoptype, None, None]
        writer.writerow(row)

def write_stops(reader, writer):
    """
    Write unique stop names per-direction
    """
    data = set((row['agency_id'], row['stop_name'], row['route_direction']) for row in reader)
    for agencyid, stopname, direction in sorted(data):
        #print agencyid, stopname, direction
        stoptype = 0
        #stopid = make_id(groupid, stopname)
        stopid = make_id(agencyid, stopname, direction)
        row = [stopid, None, stopname, None, DEFAULT_LONG,
                DEFAULT_LATT, None, None, stoptype, None, None]
        writer.writerow(row)

def write_routes(reader, writer):
    data = set((
        row['route_id'], row['agency_id'],
        row['route_short_name'], row['route_long_name'], row['route_type'],
        row['route_url'],
        ) for row in reader)
    all_route_ids = []
    for item in sorted(data):
        row = item[:4] + (None,) + item[-2:] + (None, None)
        writer.writerow(row)
        all_route_ids.append(row[0])
    #assert route_ids are unique for this file
    assert len(all_route_ids) == len(set(all_route_ids))

def write_route_stops(reader, writer):
    data = set((
        row['agency_id'], row['route_id'],
        row['stop_sequence'], row['stop_name'],
        row['route_direction']
        ) for row in reader)
    for row in sorted(data, key=lambda X: (X[0], int(X[2]))):
        stopid = make_id(row[0], row[3], row[4])
        writer.writerow((row[1], row[2], stopid, row[4]))

def write_trips_and_calendar(reader, writer1, writer2):
    alltripids = []
    sortkey = lambda X: (X['agency_id'], X['route_id'])
    data = sorted(reader, key=sortkey)
    services = {}
    for key, g in groupby(data, key=sortkey):
        # g contains one row for every stop on the route but the data
        # we want next - trip number and service id - is the same for
        # each row (in the group), so we just use the first row and continue.
        # the time schedule string should never be jagged for this to work
        # ie. each stop has a value for each trip, even if it is '...'
        agencyid, routeid = key
        row = g.next()
        direction = row['route_direction']
        headsign = row['route_end']
        tripdata = (tuple(t.split(TRIPDATAPARTJOINER)[:3]) for t in row['schedule'].split(TRIPDATAJOINER) if t)
        service_id = row['service_id']
        # inbound and outbound routes have the same service id
        service_calendar = services.setdefault(service_id, {
            'service_id': service_id,
            'monday': 0,
            'tuesday': 0,
            'wednesday': 0,
            'thursday': 0,
            'friday': 0,
            'saturday': 0,
            'sunday': 0,
            'start_date':'20110101',
            'end_date':'20991231',
        })
        for tripno, srvno, timeframe in tripdata:
            #use numeric timeframe code in trip id
            #tfname, tfweight = get_time_period_name_and_weight(timeframe)
            tripno = int(tripno)
            short_name = '%s - %s' % (srvno, headsign)
            for idx, daycode in split_timeframe(timeframe):
                idx = str(idx)
                tripid = make_trip_id(routeid, idx, tripno)
                csvrow = (routeid, service_id, tripid, headsign, short_name,
                        direction, None, None, daycode, tripno)
                writer1.writerow(csvrow)
                alltripids.append(tripid)
                dayname = daycode_to_name[daycode]
                service_calendar[dayname.lower()] = 1 # being set multiple times
    # write 'calendar.txt'
    for k in sorted(services.keys()):
        writer2.writerow(services[k])
    #assert trip_ids are unique
    assert len(alltripids) == len(set(alltripids))

def write_stop_times(reader, writer):
    alltripids = []
    for row in reader:
        agencyid = row['agency_id']
        routeid = row['route_id']
        stopname = row['stop_name']
        direction = row['route_direction']
        stopid = make_id(agencyid, stopname, direction)
        stopno = row['stop_sequence']
        stoptime_data = (tuple(t.split(TRIPDATAPARTJOINER)) for t in row['schedule'].split(TRIPDATAJOINER) if t)
        for tripno, srvno, timeframe, time in stoptime_data:
            #ignore any special instruction code for the minute
            if time == '...':
                #time = None
                continue
            else:
                time = '%s:%s:00' % (time[:2], time[2:4])
            for idx, daycode in split_timeframe(timeframe):
                idx = str(idx)
                tripid = make_trip_id(routeid, idx, tripno)
                t = (tripid, time, time, stopid, stopno, stopname, None, None, None)
                writer.writerow(t)

def get_metro_coord_map():
    coordmap = {}
    fname = pathjoin(settings.DATA_ROOT, 'translink', 'metro-coord-map.csv')
    with open(fname) as fp:
        fp.next()
        reader = csv.reader(fp)
        for row in reader:
            if len(row) >= 3:
                id = row[0].strip()
                if id:
                    coordmap[id] = row[1:3]
    return coordmap

def rewrite_stops(destroot):
    """
    The stop names as scraped directly have two problems:

        + no lat/long coords
        + the stop id is generated from the slugification of the stop name as
          given in the timetable and, while it may be the case that this
          slugification gives an unambiguously unique id for the stop, this
          can't be assumed in general

    These two issues can only be solved by updating the stops.txt file with
    information that is maintained by hand:

        + metro-coord-map.csv for coords
        + metro-stop-id-dupes.csv for ambiguous ids

    """
    stops_orig = pathjoin(destroot, 'stops_as_scraped.txt')
    stops_orig_fields = OUTFILESANDFIELDS[1][1].split()
    stops_new = pathjoin(destroot, 'stops.txt')
    stops_new_fields = stops_orig_fields
    coordmap = get_metro_coord_map()
    with open(stops_orig) as orig:
        with open(stops_new, 'wb') as new:
            new.write(orig.next())
            reader = csv.DictReader(orig, stops_orig_fields)
            writer = csv.DictWriter(new, stops_new_fields)
            for row in reader:
                coords = coordmap.get(row['stop_id'], None)
                if coords:
                    row['stop_lat'], row['stop_lon'] = coords
                writer.writerow(row)
    os.remove(stops_orig)

all_funcs = (
        write_stops,
        write_routes,
        write_route_stops,
        write_trips_and_calendar,
        write_stop_times,
)

dispatch = ((fn, t[0], t[1]) for fn, t in zip(all_funcs, OUTFILESANDFIELDS[1:-1]))

def reshape(fp, destroot=None):
    destroot = destroot or os.getcwd()
    write_agency(destroot)
    for func, outfile, fields in dispatch:
        fp.seek(0)
        reader = get_raw_csv_reader(fp)
        outfile = pathjoin(destroot, '%s.txt' % outfile)
        with open(outfile, 'wb') as fdout:
            writer = csv.writer(fdout)
            #first row is field names
            writer.writerow(fields.split())
            if func is write_trips_and_calendar:
                calfile, calfields = OUTFILESANDFIELDS[-1]
                calfile = pathjoin(destroot, '%s.txt' % calfile)
                with open(calfile, 'wb') as fp2:
                    calfields = calfields.split()
                    writer2 = csv.DictWriter(fp2, calfields)
                    writer2.writerow(dict(zip(calfields, calfields)))
                    func(reader, writer, writer2)
            else:
                func(reader, writer)
    rewrite_stops(destroot)

