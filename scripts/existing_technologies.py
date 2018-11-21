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

marginal_cost = {
    'reservoir': 0,
}

ror_mapper = {
    'RoR (MW)': 'ror'}

storage_mapper = {
    'PSP (MW)': 'phs'}

reservoir_mapper = {
    'Hydro with reservoir (MW)': 'rs'}

types = ['pumped_storage', 'reservoir', 'run_of_river']

mappers = dict(zip(types,
                   [storage_mapper, reservoir_mapper, ror_mapper]))

element_dfs = dict(zip(types,
                       [building.read_elements('pumped_storage.csv'),
                        building.read_elements('reservoir.csv'),
                        building.read_elements('run_of_river.csv')]))

elements = dict(zip(types, [{}, {}, {}]))


for country in df.index:
    for element_type, mapper in mappers.items():
        for tech_key, tech in mapper.items():
            element_name = tech + '-' + country

            if element_name in element_dfs[element_type].index:
                raise ValueError(('Element with name {}' +
                                  ' already exists!').format(element_name))



            if element_type == 'run_of_river':
                sequence_name = element_name + '_profile'

                elements[element_type][element_name] = {
                    'type': 'volatile',
                    'bus': country + '-electricity',
                    'profile': country + '-ror-profile',
                    'tech': tech,
                    'carrier': 'water',
                    'capacity': round(df.at[country, tech_key], 4)}

            elif element_type == 'pumped_storage':
                if df.at[country, tech_key] > 0:
                    elements[element_type][element_name] = {
                        'type': 'storage',
                        'tech': tech,
                        'carrier': 'water',
                        'bus': country + '-electricity',
                        'marginal_cost': 0,
                        'efficiency': 0.8,
                        'loss': 0,
                        'capacity': df.at[country, tech_key],
                        'storage_capacity': df.at[country, 'PSP reservoir (GWh)'] * 1000}

            elif element_type == 'reservoir':
                elements[element_type][element_name] = {
                    'type': 'dispatchable',
                    'tech': tech,
                    'carrier': 'water',
                    'bus': country + '-electricity',
                    'capacity': df.at[country, tech_key],
                    'marginal_cost': marginal_cost['reservoir']}


for element_type in element_dfs:
    path = building.write_elements(
            element_type + '.csv',
            pd.DataFrame.from_dict(elements[element_type], orient='index'))
