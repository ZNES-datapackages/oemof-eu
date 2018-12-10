from datapackage import Package
import pandas as pd
import json
from oemof.tools.economics import annuity

from datapackage_utilities import building

techmap = {'ocgt': 'dispatchable',
           'ccgt': 'dispatchable',
           'pv': 'volatile',
           'wind_onshore': 'volatile',
           'wind_offshore': 'volatile',
           'biomass': 'conversion',
           'lithium_battery': 'storage',
           'acaes': 'storage'}

config = building.get_config()
wacc = config['wacc']

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('electricity').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[config['year']].to_dict()

potential = Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-potential/master/datapackage.json').get_resource('renewable').read(keyed=True)
potential = pd.DataFrame(potential).set_index(['country', 'tech'])
potential = potential.loc[potential['source'] == config['potential']].to_dict()

for tech in technologies:
    technologies[tech]['capacity_cost'] = (
        technologies[tech]['capacity_cost'] * config['cost_factor'].get(tech, 1))
    if 'storage_capacity_cost' in technologies[tech]:
        technologies[tech]['storage_capacity_cost'] = (
            technologies[tech]['storage_capacity_cost'] * config['cost_factor'].get(tech, 1))

carrier = pd.read_csv('archive/carrier.csv', index_col=[0,1]).loc[('base', config['year'])]
carrier.set_index('carrier', inplace=True)

elements = {}

for r in config['regions']:
    for tech, data in technologies.items():
        if tech in config['investment_technologies']:

            element = data.copy()
            elements[r + '-' + tech] = element

            if techmap.get(tech) == 'dispatchable':
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']),
                        float(data['lifetime']), wacc) * 1000, # €/kW -> €/M
                    'bus': r + '-electricity',
                    'type': 'dispatchable',
                    'marginal_cost': (
                        carrier.loc[data['carrier']].cost +
                        carrier.loc[data['carrier']].emission *
                        carrier.loc['co2'].cost) / float(data['efficiency']),
                    'tech': tech,
                    'capacity_potential': potential['capacity_potential'].get(
                                            (r, tech), "Infinity"),
                    'edge_parameters':   json.dumps({
                        "emission_factor": (carrier.loc[data['carrier']].emission /
                                        float(data['efficiency']))
                        })
                    })

            if techmap.get(tech) == 'conversion':
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']),
                        float(data['lifetime']), wacc) * 1000, # €/kW -> €/M
                    'to_bus': r + '-electricity',
                    'from_bus': r + '-' + data['carrier'] + '-bus',
                    'type': 'conversion',
                    'marginal_cost': (
                        carrier.loc[data['carrier']].cost +
                        carrier.loc[data['carrier']].emission *
                        carrier.loc['co2'].cost) / float(data['efficiency']),
                    'tech': tech,
                    })

                    # ep = {'summed_max': float(bio_potential['value'].get(
                    #     (r, tech), 0)) * 1e6}) # TWh to MWh

            elif techmap.get(tech) == 'volatile':
                if 'wind_off' in tech:
                    profile =  r + '-wind-off-profile'
                elif 'wind_on' in tech:
                    profile =  r +  '-wind-on-profile'
                elif 'pv' in tech:
                    profile =  r + '-pv-profile'

                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']),
                        float(data['lifetime']), wacc) * 1000,
                    'capacity_potential': potential['capacity_potential'].get(
                                            (r, tech), "Infinity"),
                    'bus': r + '-electricity',
                    'tech': tech,
                    'type': 'volatile',
                    'profile': profile})

            elif techmap[tech] == 'storage':
                if tech == 'acaes' and r != 'DE':
                    capacity_potential = 0
                else:
                    capacity_potential = 'Infinity'
                element.update({
                    'capacity_cost': annuity(
                        float(data['capacity_cost']) +
                        float(data['storage_capacity_cost']) /
                        float(data['capacity_ratio']),
                        float(data['lifetime']), wacc) * 1000,
                    'bus': r + '-electricity',
                    'tech': tech,
                    'type': 'storage',
                    'efficiency': float(data['efficiency'])**0.5, # convert roundtrip to input / output efficiency
                    'marginal_cost': 0.0000001,
                    'loss': 0.01,
''                  'capacity_potential': capacity_potential,
                    'capacity_ratio': data['capacity_ratio']
                })


df = pd.DataFrame.from_dict(elements, orient='index')
# drop storage capacity cost to avoid duplicat investment
df = df.drop('storage_capacity_cost', axis=1)

df = df[(df[['capacity_potential']] != 0).all(axis=1)]

# write elements to CSV-files
for element_type in set(techmap.values()):
    path = building.write_elements(
            element_type + '.csv', df.loc[df['type'] == element_type].dropna(how='all', axis=1))
