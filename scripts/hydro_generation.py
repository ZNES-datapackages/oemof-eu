# -*- coding: utf-8 -*-
"""
"""
import logging
import json
import os
from xlrd import open_workbook, XLRDError

from datapackage import Package, Resource
import pandas as pd
from oemof.tools.economics import annuity

from datapackage_utilities import building

config = building.get_config()

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('electricity').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[config['year']].to_dict()

dirpath = building.download_data(
    "https://zenodo.org/record/804244/files/Hydro_Inflow.zip",
    unzip_file="Hydro_Inflow/")

hydro_shares = pd.DataFrame(
    Package(
        'https://raw.githubusercontent.com/ZNES-datapackages/hydro-technologies-shares/master/datapackage.json').get_resource('hydro-technologies-shares').read(keyed=True)).set_index('country')

files = os.listdir(dirpath)

x = pd.DataFrame()

_embed = lambda x: json.dumps({'summed_max': x})

for f in files:
    if any(c in f for c in config['regions']):
        df = pd.read_csv(os.path.join(dirpath, f))

        # select one year
        df = df.loc[df['Year'] == config['weather_year']]

        s = df['Inflow [GWh]']
        s.name = f.strip('.csv')
        x = pd.concat([x, s], axis=1)

total_hydro = x.sum(axis=0) * 1000 * 0.9  # GWh to MWh # DIW p.79 Table 35 Run-of-river or reservoir 2050
total_hydro.index = total_hydro.index.str[-2:]
total_hydro.index.name = 'iso-country-code'


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
                elements[element_name] = dict({
                    'type': 'volatile',
                    'bus': country + '-electricity',
                    'profile': 0.65,
                    'tech': tech,
                    'carrier': 'hydro',
                    'capacity': round(df.at[country, tech], 4)
                    }, **technologies[tech])

            elif tech == 'phs':
                if df.at[country, tech] > 0:
                    elements[element_name] = dict({
                        'type': 'storage',
                        'tech': tech,
                        'carrier': 'hydro',
                        'bus': country + '-electricity',
                        'loss': 0,
                        'capacity': df.at[country, tech],
                        'storage_capacity': df.at[country, 'PSP reservoir (GWh)'] * 1000 # to MWh
                    }, **technologies[tech])

            elif tech == 'reservoir':
                if df.at[country, tech] > 0:
                    if country not in ['LU', 'NL']:
                        production = (
                            total_hydro[country] *
                            float(hydro_shares.at[country, 'reservoir']))
                    else:
                        production = 0
                    elements[element_name] = dict({
                        'type': 'dispatchable',
                        'tech': tech,
                        'carrier': 'hydro',
                        'bus': country + '-electricity',
                        'edge_parameters': _embed(production / df.at[country, tech]),
                        'capacity': df.at[country, tech]
                    }, **technologies[tech])

df = pd.DataFrame.from_dict(elements, orient='index')

#
df['capacity_cost'] = df.apply(
    lambda x: annuity(float(x['capacity_cost']) * 1000,
                      float(x['lifetime']),
                      config['wacc']), axis=1)

for tech, element_type in techmap.items():
    path = building.write_elements(
            tech + '.csv',
            df.loc[df['type'] == element_type].dropna(how='all', axis=1))
