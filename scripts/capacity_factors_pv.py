# -*- coding: utf-8 -*-
"""
"""
import json
import pandas as pd

from datapackage_utilities import building

config = building.get_config()

filepath = building.download_data(
    "https://www.renewables.ninja/static/downloads/ninja_europe_pv_v1.1.zip",
    unzip_file='ninja_pv_europe_v1.1_merra2.csv')

year = str(config['weather_year'])

countries = config['regions']

raw_data = pd.read_csv(filepath, index_col=[0], parse_dates=True)

df = raw_data.loc[year]

sequences_df = pd.DataFrame(index=df.index)

for c in countries:
    sequence_name = 'pv-' + c + '-profile'
    sequences_df[sequence_name] = raw_data.loc[year][c].values

sequences_df.index = building.timeindex()
path = building.write_sequences('volatile_profile.csv', sequences_df)
