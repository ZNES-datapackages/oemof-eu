# -*- coding: utf-8 -*-
"""
"""
import json
import os
import pandas as pd

from datapackage_utilities import building

config = building.get_config()

dirpath = building.download_data(
    "https://zenodo.org/record/804244/files/Hydro_Inflow.zip",
    unzip_file="Hydro_Inflow/")

files = os.listdir(dirpath)

x = pd.DataFrame()

reservoir_elements = building.read_elements('reservoir.csv')

ror_elements = building.read_elements('run_of_river.csv')
ror_elements.reset_index(inplace=True)
ror_elements.set_index(ror_elements['bus'].str[:2], inplace=True)
ror_elements.index.name = 'iso-country-code'

_embed = lambda x: json.dumps({'summed_max': x})

for f in files:
    if any(c in f for c in config['regions']):
        df = pd.read_csv(os.path.join(dirpath, f))

        # select one year
        df = df.loc[df['Year'] == config['weather_year']]

        s = df['Inflow [GWh]']
        s.name = f.strip('.csv')
        x = pd.concat([x, s], axis=1)

e = x.sum(axis=0) * 1000 * 0.9  # GWh to MWh # DIW p.79 Table 35 Run-of-river or reservoir 2050
e.index = e.index.str[-2:]
e.index.name = 'iso-country-code'

ror_elements['_capacity'] = ror_elements['bus'].map(
    dict(reservoir_elements[['bus', 'capacity']].values))
ror_elements['_inflow'] = e

ror_elements['_summed_max'] = 1 / (ror_elements['capacity'] + ror_elements['_capacity']) * ror_elements['_inflow']
ror_elements['_summed_max'].fillna(ror_elements['_summed_max'].mean(), inplace=True)

ror_elements['edge_parameters'] = ror_elements['_summed_max'].apply(_embed)
ror_elements.drop(['_capacity', '_summed_max', '_inflow'], axis=1, inplace=True)

reservoir_elements['edge_parameters'] = \
    reservoir_elements['bus'].str[:2].map(ror_elements['edge_parameters'])

#ror_elements.set_index('name', inplace=True)

#path = building.write_elements('run_of_river.csv', ror_elements, replace=True)

path = building.write_elements('reservoir.csv', reservoir_elements, replace=True)
