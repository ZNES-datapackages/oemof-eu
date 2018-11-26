# -*- coding: utf-8 -*-
"""
"""
import json
from datapackage import Resource, Package
import pandas as pd
from datapackage_utilities import building

config = building.get_config()

elements = []
for b in config.get('central_heat_buses', []):
    elements.append({
        'name': b + '-load',
        'type': 'load',
        'bus': b,
        'amount': 200 * 1e6, # 190.000.000 MWh i.e. 190 TWh
        'profile': 'DE-heat-profile',
        'carrier': 'heat'
        }
    )

for b in config.get('decentral_heat_buses', []):
    elements.append({
        'name': b + '-load',
        'type': 'load',
        'bus': b,
        'amount': 200 * 1e6,
        'profile': 'DE-heat-profile',
        'carrier': 'heat'
        }
    )

path = building.write_elements(
    'load.csv', pd.DataFrame(elements).set_index('name'))

heat_demand_profile = pd.Series(
    data=pd.read_csv('archive/thermal_load_profile.csv', sep=";")['thermal_load'].values,
    index=pd.date_range(str(config['year']), periods=8760, freq='H'))
heat_demand_profile.rename('DE-heat-profile', inplace=True)

path = building.write_sequences('load_profile.csv', heat_demand_profile)
