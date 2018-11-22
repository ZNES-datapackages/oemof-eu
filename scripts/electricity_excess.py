# -*- coding: utf-8 -*-
"""
"""
import json
import pandas as pd

from datapackage_utilities import building, processing


config = building.get_config()

buses = building.read_elements('bus.csv')
buses.index.name = 'bus'

elements = pd.DataFrame(buses.index)

elements['type'] = 'excess'
elements['name'] = 'excess-' + elements['bus'] 
elements['marginal_cost'] = 0

elements.set_index('name', inplace=True)

path = building.write_elements('excess.csv', elements)
