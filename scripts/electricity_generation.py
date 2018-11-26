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


technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('electricity').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[config['year']].to_dict()


potential = Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-potential/master/datapackage.json').get_resource('renewable').read(keyed=True)
potential = pd.DataFrame(potential).set_index(['country', 'tech']).to_dict()

carrier = pd.read_csv('archive/carrier.csv', index_col=[0,1]).loc[('base', config['year'])]
carrier.set_index('carrier', inplace=True)

elements = {}

for r in config['regions']:
    for tech, data in technologies.items():
        if tech in config['investment_technologies']:

            element = data.copy()
            elements[tech + '-' + r] = element

            if techmap[tech] == 'dispatchable':
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']),
                        float(data['lifetime']), 0.07) * 1000, # €/kW -> €/M
                    'bus': r + '-electricity',
                    'type': 'dispatchable',
                    'marginal_cost': (
                        carrier.loc[data['carrier']].cost +
                        carrier.loc[data['carrier']].emission *
                        carrier.loc['co2'].cost) / float(data['efficiency']),
                    'tech': tech,
                    'capacity_potential': potential['capacity_potential'].get(
                                            (r, tech), "Infinity"),
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
                        float(data['capacity_cost']),
                        float(data['lifetime']), 0.07) * 1000,
                    'capacity_potential': potential['capacity_potential'].get(
                                            (r, tech), "Infinity"),
                    'bus': r + '-electricity',
                    'tech': tech,
                    'type': 'volatile',
                    'profile': profile})


df = pd.DataFrame.from_dict(elements, orient='index')

df = df[(df[['capacity_potential']] != 0).all(axis=1)]

# write elements to CSV-files
for element_type in set(techmap.values()):
    path = building.write_elements(
            element_type + '.csv', df.loc[df['type'] == element_type].dropna(how='all', axis=1))
