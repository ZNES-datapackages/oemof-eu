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
        'gas_heatpump': 'conversion',
    }

config = building.get_config()

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('decentral_heat').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[config['year']].to_dict()

carrier = pd.read_csv('archive/carrier.csv', index_col=[0,1]).loc[('base', config['year'])]
carrier.set_index('carrier', inplace=True)

elements = list()

for b in config.get('decentral_heat_buses', []):
    for tech, entry in technologies.items():
        element_name = tech + '-' + b
        print(element_name)

        if techmap.get(tech) == 'backpressure':
            elements.append({
                'name': element_name,
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
                                         entry['lifetime'], 0.07)
            })

        elif techmap.get(tech) == 'extraction':
            elements.append({
                'name': element_name,
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
                                         entry['lifetime'], 0.07)
            })

        elif techmap.get(tech) == 'dispatchable':
            elements.append({
                'name': element_name,
                'type': techmap[tech],
                'carrier': entry['carrier'],
                'marginal_cost': carrier.at[entry['carrier'], 'cost'] / float(entry['thermal_efficiency']),
                'electricity_bus': 'DE-electricity',
                'heat_bus': b,
                'edge_parameters': json.dumps(
                    {"emission_factor": carrier.at[entry['carrier'], 'emission']}),
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         entry['lifetime'], 0.07)
            })

        elif techmap.get(tech) == 'conversion':
            elements.append({
                'name': element_name,
                'type': techmap[tech],
                'fuel_bus': 'GL-gas',
                'carrier': entry['carrier'],
                'electricity_bus': 'DE-electricity',
                'heat_bus': b,
                'efficiency': entry['thermal_efficiency'],
                'capacity_potential': 'Infinity',
                'tech': tech,
                'capacity_cost': annuity(float(entry['capacity_cost']),
                                         entry['lifetime'], 0.07)
            })


elements = pd.DataFrame(elements)
elements.set_index('name', inplace=True)

for type in set(techmap.values()):
    building.write_elements(type + '.csv', elements.loc[elements['type'] == type])



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
