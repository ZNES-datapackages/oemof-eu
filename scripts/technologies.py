import pandas as pd
import json

from datapackage_utilities import building

config = building.get_config()

investment_technologies = [
    'wind_onshore', 'wind_offshore', 'pv_rooftop', 'ocgt', 'ccgt',
    'battery', 'coal', 'caes']

def annuity(capex, n, wacc):
    return capex * (wacc * (1 + wacc) ** n) / ((1 + wacc) ** n - 1)

all_technologies = pd.read_csv('archive/technologies.csv', index_col=0)
carrier = pd.read_csv('archive/carrier.csv')
carrier[(carrier['year'] == config['year']) & (carrier['scenario'] == 'base')]
carrier.set_index('carrier', inplace=True)

types = config['sources']

element_dfs = {t: building.read_elements(t + '.csv') for t in types}

buses = [b + '-electricity' for b in config['buses']]

data = dict(zip(types, [{},{},{}]))

all_technologies.index = all_technologies.index.str.replace(' ', '_')

for idx, row in all_technologies.iterrows():
    if idx in investment_technologies:
        for b in buses:
            if 'wind_off' in idx and b.strip('-electricity') not in [
                'BE', 'DE', 'DK', 'FI', 'FR', 'GB', 'IE', 'IT', 'NL', 'NO',
                'SE']:
                pass
            else:
                element_name = idx + '_' + b
                element = dict(row)

                if row['type'] == 'dispatchable':
                    element.update({
                        'capacity_cost': annuity(
                            row['Investment in Euro/kW'], row['lifetime'], 0.07) * 1000,
                        'capacity_potential': None,
                        'bus': b,
                        'marginal_cost': (
                            carrier.loc[row['carrier']].cost +
                            carrier.loc[row['carrier']].emission *
                            carrier.loc['co2'].cost) / row['efficiency'],
                        'tech': idx,
                        'edge_parameters': json.dumps({
                            "emission_factor":  (carrier.loc[row['carrier']].emission /
                                                  row['efficiency'])
                            })
                        })

                if row['type'] == 'volatile':
                    if 'wind_off' in idx:
                        profile = 'wind-off-' + b.strip('-electricity') + '-profile'
                    elif 'wind' in idx:
                        profile = 'wind-' + b.strip('-electricity') + '-profile'
                    elif 'pv' in idx:
                        profile = 'pv-' + b.strip('-electricity') + '-profile'
                    element.update({
                        'capacity_cost': annuity(
                            row['Investment in Euro/kW'], row['lifetime'], 0.07) * 1000,
                        'capacity_potential': None,
                        'bus': b,
                        'tech': idx,
                        'profile': profile})

                if row['type'] == 'storage':
                    if 'battery' in idx:
                        cr = 0.2
                    if 'caes' in idx:
                        cr = 0.125
                    element.update({
                        'bus': b,
                        'tech': idx,
                        'efficiency': row['efficiency'],
                        'capacity_ratio': cr,
                        'capacity_cost': annuity(
                            row['Investment in Euro/kW'], row['lifetime'], 0.07) * 1000,
                        'loss': 0})

                data[row['type']][element_name] = element

# write elements to CSV-files
for element_type in element_dfs:
    path = building.write_elements(
            element_type + '.csv',
            pd.DataFrame.from_dict(data[element_type], orient='index'))
