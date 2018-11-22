# -*- coding: utf-8 -*-
"""
This script constructs a pandas.Series `buses` with hub-names as index and
polygons of these buses as values. It uses the NUTS shapefile.

"""
import json
import pandas as pd
from geojson import FeatureCollection, Feature

from datapackage_utilities import building, geometry


config = building.get_config()

# Add bus geomtries
filepath = building.download_data(
    'http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/'\
    'NUTS_2013_10M_SH.zip',
    unzip_file = 'NUTS_2013_10M_SH/data/NUTS_RG_10M_2013.shp')

building.download_data(
    'http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/'\
    'NUTS_2013_10M_SH.zip',
    unzip_file = 'NUTS_2013_10M_SH/data/NUTS_RG_10M_2013.dbf')

# get nuts 1 regions for german neighbours
nuts0 = pd.Series(geometry.nuts(filepath, nuts=0, tolerance=0.1))

buses = pd.Series(name='geometry')
buses.index.name= 'name'

for r in config['regions']:
    buses[r + '-electricity'] = nuts0[r]
building.write_geometries('bus.geojson', buses)

# Add electricity buses
hub_elements = {}
for b in buses.index:
    hub_elements[b] = {
        'type': 'bus',
        'carrier': 'electricity',
        'geometry': b,
        'balanced': True}

# Add heat buses
for b in config.get('central_heat_buses', []):
    hub_elements[b] = {
        'type': 'bus',
        'carrier': 'heat',
        'geometry': None,
        'balanced': True}

for b in config.get('decentral_heat_buses', []):
    hub_elements[b] = {
        'type': 'bus',
        'carrier': 'heat',
        'geometry': None,
        'balanced': True}


# Add global buses
for b in config.get('global_buses', []):
    hub_elements[b] = {
        'type': 'bus',
        'carrier': b.split('-')[1],
        'geometry': None,
        'balanced': False}

path = building.write_elements(
            'bus.csv',
            pd.DataFrame.from_dict(hub_elements, orient='index'))
