
TRANSLINK_URL = 'http://www.translink.co.uk'
metro_index_fmt = TRANSLINK_URL + '/Metro/Metro-Timetables/Metro-%s-Timetables/'
TRANSLINK_METRO_INDEX_URLS = [
    metro_index_fmt % i for i in range(1, 13)
] + [
    metro_index_fmt % '910',
]
TRANSLINK_ID = 'translinkni'
TRANSLINK_NAME = 'Translink N.I.'
METRO_ID = TRANSLINK_ID + '-metro'
METRO_NAME = 'Translink N.I. (Metro)'

BUSROUTETYPE = 3
RAILROUTETYPE = 2
DIRECTIONCODES = {'inbound': 1, 'outbound': 0}
