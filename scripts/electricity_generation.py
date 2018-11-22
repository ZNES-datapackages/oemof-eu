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
           'biomass': 'dispatchable'}

config = building.get_config()

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('generation').read(keyed=True))
technologies.set_index('tech', inplace=True)

potential = Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-potential/master/datapackage.json').get_resource('renewable').read(keyed=True)
potential = pd.DataFrame(potential).set_index(['country', 'tech']).to_dict()

carrier = pd.read_csv('archive/carrier.csv', index_col=[0,1]).loc[('base', config['year'])]
carrier.set_index('carrier', inplace=True)

element_dfs = {t: building.read_elements(t + '.csv') for t in config['sources']}

elements = dict(zip([i for i in element_dfs.keys()], [{},{},{}]))

for tech, data in technologies.iterrows():
    if tech in config['investment_technologies']:
        for r in config['regions']:
            element_name = tech + '-' + r
            element = dict(data)

            if techmap[tech] == 'dispatchable':
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']), data['lifetime'], 0.07) * 1000,
                    'bus': r + '-electricity',
                    'type': 'dispatchable',
                    'marginal_cost': (
                        carrier.loc[data['carrier']].cost +
                        carrier.loc[data['carrier']].emission *
                        carrier.loc['co2'].cost) / float(data['efficiency']),
                    'tech': tech,
''                        'capacity_potential': potential['capacity_potential'].get((r, tech), "Infinity"),
                    'edge_parameters': json.dumps({
                        "emission_factor":  (carrier.loc[data['carrier']].emission /
                                              float(data['efficiency']))
                        })
                    })

            elif techmap[tech] == 'volatile':
                if 'wind_off' in tech:
                    profile = 'wind-off-' + r + '-profile'
                elif 'wind_on' in tech:
                    profile = 'wind-' + r + '-profile'
                elif 'pv' in tech:
                    profile = 'pv-' + r + '-profile'
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']), data['lifetime'], 0.07) * 1000,
                    'capacity_potential': potential['capacity_potential'].get((r, tech), "Infinity"),
                    'bus': r + '-electricity',
                    'tech': tech,
                    'type': 'volatile',
                    'profile': profile})

            elements[techmap[tech]][element_name] = element

# write elements to CSV-files
for element_type in element_dfs:
    path = building.write_elements(
            element_type + '.csv',
            pd.DataFrame.from_dict(elements[element_type], orient='index'))
