# -*- coding: utf-8 -*-
""" Use long term ninja capacity factors to produce wind profiles.
"""
import pandas as pd

from datapackage_utilities import building


config = building.get_config()

# on_filepath = building.download_data(
#     'https://www.renewables.ninja/static/downloads/ninja_europe_wind_v1.1.zip',
#     unzip_file='ninja_wind_europe_v1.1_future_longterm_national.csv')

off_filepath = building.download_data(
    'https://www.renewables.ninja/static/downloads/ninja_europe_wind_v1.1.zip',
    unzip_file='ninja_wind_europe_v1.1_future_nearterm_on-offshore.csv')

near_term_path = building.download_data(
    'https://www.renewables.ninja/static/downloads/ninja_europe_wind_v1.1.zip',
    unzip_file='ninja_wind_europe_v1.1_current_national.csv')

year = str(config['weather_year'])

# not in ninja dataset, as new market zones? (replace by german factor)
missing = ['LU' 'CZ' 'AT' 'CH']

countries = list(set(config['regions']) - set(missing))

near_term = pd.read_csv(near_term_path, index_col=[0], parse_dates=True)

offshore_data = pd.read_csv(off_filepath, index_col=[0], parse_dates=True)

sequences_df = pd.DataFrame(index=near_term.loc[year].index)

for c in config['regions']:
    # add offshore profile if country exists in offshore data columns
    if [col for col in offshore_data.columns if c + '_OFF' in col]:
        sequences_df['wind-off-' + c + '-profile'] = offshore_data[c + '_OFF']
    # hack as poland is not in ninja, therfore we take SE offshore profile
    elif c == 'PL':
        sequences_df['wind-off-' + c + '-profile'] = offshore_data['SE_OFF']

    sequence_name = 'wind-' + c + '-profile'

    sequences_df[sequence_name] =  near_term.loc[year][c].values

sequences_df.index = building.timeindex()

path = building.write_sequences('volatile_profile.csv', sequences_df)
