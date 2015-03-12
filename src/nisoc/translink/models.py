
from django.db import models
from django.core.urlresolvers import reverse


class AgencyGroup(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    desc = models.CharField(max_length=250)
    url = models.URLField(blank=True, null=True)
    country = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Agency(models.Model):
    group = models.ForeignKey(AgencyGroup)
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50)
    url = models.URLField()
    timezone = models.CharField(max_length=2)
    lang = models.CharField(max_length=2, default='EN', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __unicode__(self):
        return self.name

class Stop(models.Model):
    LOCATION_TYPES = (
            ( 0, 'Stop' ),
            ( 1, 'Station' ),
    )
    group = models.ForeignKey(AgencyGroup)
    id = models.SlugField(max_length=110, primary_key=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=100)
    desc = models.TextField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    zone_id = models.CharField(max_length=10, blank=True, null=True)
    stop_url = models.URLField(blank=True, null=True)
    location_type = models.PositiveSmallIntegerField(choices=LOCATION_TYPES, blank=True, null=True)
    parent_station = models.CharField(max_length=110, blank=True, null=True)

    def __unicode__(self):
        return self.name

class Route(models.Model):
    ROUTE_TYPES = (
            (0, 'Tram, Streetcar, Light Rail'),
            (1, 'Subway, Metro'),
            (2, 'Rail. Intercity or long-distance train routes.'),
            (3, 'Bus. Short and long-distance bus routes.'),
            (4, 'Ferry.'),
    )
    id = models.CharField(max_length=30, primary_key=True)
    agency = models.ForeignKey(Agency)
    short_name = models.CharField(max_length=20, blank=True, null=True)
    long_name = models.CharField(max_length=100, blank=True, null=True)
    route_type = models.PositiveSmallIntegerField(choices=ROUTE_TYPES)
    url = models.URLField(blank=True, null=True)
    desc = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=6, blank=True, null=True)
    text_color = models.CharField(max_length=6, blank=True, null=True)
    stops = models.ManyToManyField(Stop, through='RouteStop')

    def __unicode__(self):
        return self.long_name

    def get_absolute_url(self):
        return reverse('onyroad-timetable-view', [self.id])

class RouteStop(models.Model):
    route = models.ForeignKey(Route)
    sequence = models.PositiveIntegerField()
    stop = models.ForeignKey(Stop)
    direction = models.PositiveSmallIntegerField()

class TimeFrame(models.Model):
    name = models.CharField(max_length=16, unique=True)
    tab_order = models.PositiveIntegerField()
    display_name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Trip(models.Model):
    DIRECTION_TYPES = (
            (0, 'Outbound'),
            (1, 'Inbound'),
    )
#    TIMEFRAME_TYPES = (
#            ('WK', 'Monday-Friday'),
#            ('SA', 'Saturday'),
#            ('SU', 'Sunday'),
#            ('HIS', 'High Season'),
#            ('LOS', 'Low Season'),
#    )
    route = models.ForeignKey(Route)
    service_id = models.CharField(max_length=30)
    id = models.CharField(max_length=60, primary_key=True)
    sequence = models.PositiveIntegerField()
    #timeframe = models.CharField(max_length=6, choices=TIMEFRAME_TYPES, blank=True, null=True)
    timeframe = models.ForeignKey(TimeFrame)
    headsign = models.CharField(max_length=100, blank=True, null=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    direction_id = models.PositiveSmallIntegerField(choices=DIRECTION_TYPES, default=0, blank=True, null=True)
    block_id = models.CharField(max_length=50, blank=True, null=True)
    shape_id = models.CharField(max_length=50, blank=True, null=True)

    def __unicode__(self):
        return u'%s - %s - %s' % (self.timeframe, self.service_id, self.route)

class StopTime(models.Model):
    PICKUP_TYPES = (
            (0, 'Regularly scheduled pick up'),
            (1, 'No pickup available'),
    )
    DROPOFF_TYPES = (
            (0, 'Regularly scheduled drop off'),
            (1, 'No drop off available'),
    )
    trip = models.ForeignKey(Trip)
    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)
    stop = models.ForeignKey(Stop)
    stop_sequence = models.PositiveIntegerField()
    stop_headsign = models.CharField(max_length=100, blank=True, null=True)
    pickup_type = models.PositiveSmallIntegerField(default=0, choices=PICKUP_TYPES, blank=True, null=True)
    dropoff_type = models.PositiveSmallIntegerField(default=0, choices=DROPOFF_TYPES, blank=True, null=True)
    shape_dist_travelled = models.FloatField(blank=True, null=True)


