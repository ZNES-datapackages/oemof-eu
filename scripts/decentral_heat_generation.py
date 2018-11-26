# -*- coding: utf-8 -*-
"""
"""
import json
from datapackage import Resource, Package
import pandas as pd
from oemof.tools.economics import annuity
from datapackage_utilities import building

techmap = {
        'extraction': 'extraction',
        'boiler_decentral': 'dispatchable',
        'electricity_heatpump': 'conversion',
        'gas_heatpump': 'dispatchable',
    }

config = building.get_config()

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('decentral_heat').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[config['year']].to_dict()

carrier = pd.read_csv('archive/carrier.csv', index_col=[0,1]).loc[('base', config['year'])]
carrier.set_index('carrier', inplace=True)

elements = dict()

for b in config.get('decentral_heat_buses', []):
    for tech, entry in technologies.items():
        element_name = tech + '-' + b

        element = entry.copy()
        
        elements[element_name] = element

        if techmap.get(tech) == 'backpressure':
            element.update({
                'type': techmap[tech],
                'fuel_bus': 'GL-gas',
                'carrier': entry['carrier'],
                'fuel_cost': carrier.at[entry['carrier'], 'cost'],
                'electricity_bus': 'DE-electricity',
                'heat_bus': b,
                'thermal_efficiency': entry['thermal_efficiency'],
                'input_edge_parameters': json.dumps(
                    {"emission_factor": carrier.at[entry['carrier'], 'emission']}),
                'electric_efficiency': entry['electrical_efficiency'],
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         float(entry['lifetime']), 0.07)
            })

        elif techmap.get(tech) == 'extraction':
            element.update({
                'type': techmap[tech],
                'carrier': entry['carrier'],
                'fuel_bus': 'GL-gas',
                'fuel_cost': carrier.at[entry['carrier'], 'cost'],
                'electricity_bus': 'DE-electricity',
                'heat_bus': b,
                'thermal_efficiency': entry['thermal_efficiency'],
                'input_edge_parameters': json.dumps(
                    {"emission_factor": carrier.at[entry['carrier'], 'emission']}),
                'electric_efficiency': entry['electrical_efficiency'],
                'condensing_efficiency': entry['condensing_efficiency'],
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         float(entry['lifetime']), 0.07)
            })

        elif techmap.get(tech) == 'dispatchable':
            element.update({
                'type': techmap[tech],
                'carrier': entry['carrier'],
                'marginal_cost': (carrier.at[entry['carrier'], 'cost'] /
                                  float(entry['efficiency'])),
                'bus': b,
                'edge_parameters': json.dumps(
                    {"emission_factor": carrier.at[entry['carrier'], 'emission']}),
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         float(entry['lifetime']), 0.07)
            })

        elif techmap.get(tech) == 'conversion':
            element.update({
                'type': techmap[tech],
                'carrier': entry['carrier'],
                'from_bus': 'DE-electricity',
                'to_bus': b,
                'efficiency': entry['efficiency'],
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         float(entry['lifetime']), 0.07)
            })


elements = pd.DataFrame.from_dict(elements, orient='index')


for type in set(techmap.values()):
    building.write_elements(type + '.csv',
            elements.loc[elements['type'] == type].dropna(how='all', axis=1))



#
# heat_storage = {
#     'heat-storage-DE': {
#         'type': 'storage',
#         'bus': 'DE-heat',
#         'tech': 'heat-storage',
#         'capacity_potential': 'Infinity',
#         'efficiency': 1,
#         'loss': 0.0,
#         'capacity_ratio': 1/6,
#         'capacity_cost': investment_cost['heat-storage']
#     }
# }
#
