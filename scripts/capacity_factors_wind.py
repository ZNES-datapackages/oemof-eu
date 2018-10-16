# -*- coding: utf-8 -*-
""" Use long term ninja capacity factors to produce wind profiles.
"""
import pandas as pd

from datapackage_utilities import building


config = building.get_config()

filepath = building.download_data(
    'https://www.renewables.ninja/static/downloads/ninja_europe_wind_v1.1.zip',
    unzip_file='ninja_wind_europe_v1.1_future_longterm_national.csv')

year = str(config['weather_year'])

# not in ninja dataset, as new market zones? (replace by german factor)
missing = ['LU' 'CZ' 'AT' 'CH']
countries = list(set(config['buses']) - set(['LU', 'CZ', 'AT', 'CH']))

raw_data = pd.read_csv(filepath, index_col=[0], parse_dates=True)

df = raw_data.loc[year][countries]

sequences_df = pd.DataFrame(index=df.index)

for c in config['buses']:
    sequence_name = 'wind-' + c + '-profile'
    if c == 'LU':
        sequences_df[sequence_name] = df['BE'].values
    elif c == 'CZ':
        sequences_df[sequence_name] = df['PL'].values
    elif c in ['AT', 'CH']:
        sequences_df[sequence_name] = df['FR'].values
    else:
        sequences_df[sequence_name] = df[c].values

sequences_df.index = building.timeindex()

path = building.write_sequences('volatile_profile.csv', sequences_df)
