#!/usr/bin/env python

from setuptools import setup, find_packages


__version__ = '0.0.2'

readme = open("README").read()
changes = open("docs/changes.rst").read()
long_description = readme + "\n\n" + changes


setup(
    name="django-nisoc",
    version=__version__,
    author="Djord Flanagan",
    author_email="grflanagan@gmail.com",
    description="Northern Ireland dataset scrapers",
    long_description=long_description,
    download_url="http://pypi.python.org/packages/source/d/django-nisoc/django-nisoc-%s.tar.gz" % __version__,
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    package_data = {'nisoc': [
        'data/translink/*.*',
    ]},
    entry_points = {
        "console_scripts": [
          "gtfs_validate = nisoc.scripts.gtfs_feed_validator:main",
          "gtfs_view = nisoc.scripts.gtfs_schedule_viewer:main",
          "generate_metro_stops = nisoc.translink.generate_metro_stops:main",
        ]
    }
)

