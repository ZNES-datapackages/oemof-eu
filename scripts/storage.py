from datapackage import Package
import pandas as pd
import json
from oemof.tools.economics import annuity

from datapackage_utilities import building


techmap = {'ocgt': 'dispatchable',
           'ccgt': 'dispatchable',
           'stsc': 'dispatchable',
           'pv': 'volatile',
           'wind_onshore': 'volatile',
           'wind_offshore': 'volatile',
           'biomass': 'dispatchable',
           'battery': 'storage'}

config = building.get_config()

storages = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('storage').read(keyed=True))
storages = storages.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
storages = storages.loc[config['year']].to_dict()

potential = Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-potential/master/datapackage.json').get_resource('storage').read(keyed=True)
potential = pd.DataFrame(potential).set_index(['country', 'tech']).to_dict()

elements = {}
for tech, data in storages.items():
    if tech in config['investment_technologies']:
        for r in config['regions']:
            element_name = tech + '_' + r
            element = dict(data)

            if techmap[tech] == 'storage':
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']) + float(data['storage_capacity_cost']) / float(data['capacity_ratio']), float(data['lifetime']), 0.07) * 1000,
                    'bus': r + '-electricity',
                    'tech': tech,
                    'type': 'storage',
''                  'capacity_potential': potential['capacity_potential'].get((r, tech), "Infinity"),
                    'capacity_ratio': data['capacity_ratio']
                    })

            elements[element_name] = element


path = building.write_elements('storage.csv',
                               pd.DataFrame.from_dict(elements, orient='index'))
