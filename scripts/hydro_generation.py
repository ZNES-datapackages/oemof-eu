# -*- coding: utf-8 -*-
"""
"""
import logging
import json
import os
from xlrd import open_workbook, XLRDError

from datapackage import Package, Resource
import pandas as pd

from datapackage_utilities import building

config = building.get_config()

filename = 'e-Highway2050_2050_Country_and_cluster_installed_capacities_31-03-2015.xlsx'
filepath = os.path.join('archive', filename)

if os.path.exists(filepath):
    df = pd.read_excel(filepath, sheet_name='Country_X-7', index_col=[0])
else:
    logging.info('File for e-Highway capacities does not exist. Download..')
    filepath = building.download_data(
        'http://www.e-highway2050.eu/fileadmin/documents/Results/'  +
        filename)
    try:
        book = open_workbook(filepath)
        df = pd.read_excel(filepath, sheet_name='Country_X-7', index_col=[0])
    except XLRDError as e:
        raise XLRDError('Downloaded file not valid xlsx file.')

df = df.loc[config['regions']]

techmap = {
    'ror': 'volatile',
    'phs': 'storage',
    'reservoir': 'dispatchable'}

df.rename(columns={
            'RoR (MW)': 'ror',
            'PSP (MW)': 'phs',
            'Hydro with reservoir (MW)': 'reservoir'},
        inplace=True)

elements = {}

for country in config['regions']:
    for tech in techmap:
            element_name = tech + '-' + country

            if tech == 'ror':
                elements[element_name] = {
                    'type': 'volatile',
                    'bus': country + '-electricity',
                    'profile': 0.65,
                    'tech': tech,
                    'carrier': 'hydro',
                    'capacity': round(df.at[country, tech], 4)}

            elif tech == 'phs':
                if df.at[country, tech] > 0:
                    elements[element_name] = {
                        'type': 'storage',
                        'tech': tech,
                        'carrier': 'hydro',
                        'bus': country + '-electricity',
                        'efficiency': 0.8,
                        'loss': 0,
                        'capacity': df.at[country, tech],
                        'storage_capacity': df.at[country, 'PSP reservoir (GWh)'] * 1000
                    } # to MWh

            elif tech == 'reservoir':
                elements[element_name] = {
                    'type': 'dispatchable',
                    'tech': tech,
                    'carrier': 'hydro',
                    'bus': country + '-electricity',
                    'capacity': df.at[country, tech]
                }

df = pd.DataFrame.from_dict(elements, orient='index')

for element_type in techmap.values():
    path = building.write_elements(
            element_type + '.csv',
            df.loc[df['type'] == element_type].dropna(how='all', axis=1))
