# -*- coding: utf-8 -*-
"""
"""
import json
import pandas as pd

from datapackage_utilities import building

config = building.get_config()

year = str(config['weather_year'])

sequences_df = pd.DataFrame(index=building.timeindex())

elements = building.read_elements('run_of_river.csv')
for c in config['regions']:
    # get sequence name from elements edge_parameters (include re-exp to also
    # check for 'elec' or similar)
    sequence_name = elements.at[
            elements.index[elements.index.str.contains(c)][0],
            'profile']

    sequences_df[sequence_name] = 0.65

sequences_df.index = building.timeindex()

path = building.write_sequences('run_of_river_profile.csv', sequences_df)
