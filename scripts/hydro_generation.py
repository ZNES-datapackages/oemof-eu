"""
"""

import os

import pandas as pd

from datapackage import Package
from datapackage_utilities import building

from oemof.tools.economics import annuity

def get_hydro_inflow(inflow_dir=None):
    """ Adapted from https://github.com/FRESNA/vresutils/blob/master/vresutils/hydro.py
    """

    def read_inflow(country):
        return (pd.read_csv(os.path.join(inflow_dir,
                                         'Hydro_Inflow_{}.csv'.format(country)),
                            parse_dates={'date': [0,1,2]})
                .set_index('date')['Inflow [GWh]'])

    europe = ['AT','BA','BE','BG','CH','CZ','DE',
              'ES','FI','FR','HR','HU','IE','IT','KV',
              'LT','LV','ME','MK','NL','NO','PL','PT',
              'RO','RS','SE','SI','SK']

    hyd = pd.DataFrame({cname: read_inflow(cname) for cname in europe})

    hydro = hyd.resample('H').interpolate('cubic')

    if True: #default norm
        normalization_factor = (hydro.index.size/float(hyd.index.size)) #normalize to new sampling frequency
    else:
        normalization_factor = hydro.sum() / hyd.sum() #conserve total inflow for each country separately
    hydro /= normalization_factor
    return hydro


config = building.get_config()
countries, year = config['regions'], config['year']

capacities = pd.read_csv(building.download_data(
    'https://zenodo.org/record/804244/files/hydropower.csv?download=1'),
    index_col=['ctrcode'])

capacities.loc['CH'] = [8.8, 12, 1.9]  # add CH elsewhere

inflows = (get_hydro_inflow(building.download_data(
        'https://zenodo.org/record/804244/files/Hydro_Inflow.zip?download=1',
        unzip_file='Hydro_Inflow/')))

inflows = inflows.loc[inflows.index.year == config['weather_year'], :]
inflows['DK'], inflows['LU'] = 0, inflows['BE']

technologies = pd.DataFrame(Package('https://raw.githubusercontent.com/ZNES-datapackages/technology-cost/master/datapackage.json').get_resource('electricity').read(keyed=True))
technologies = technologies.groupby(['year', 'tech', 'carrier']).apply(lambda x: dict(zip(x.parameter, x.value))).reset_index('carrier').apply(lambda x: dict({'carrier': x.carrier}, **x[0]), axis=1)
technologies = technologies.loc[year].to_dict()

ror_shares = pd.read_csv(building.download_data(
    'https://zenodo.org/record/804244/files/Run-Of-River%20Shares.csv?download=1'),
    index_col=['ctrcode'])['run-of-river share']

# ror
ror = pd.DataFrame(index=countries)
ror['type'], ror['tech'], ror['bus'], ror['capacity'] = \
    'volatile', \
    'ror', \
    ror.index.astype(str) + '-electricity', \
    ror_shares[ror.index] * capacities.loc[ror.index, ' installed hydro capacities [GW]'] * 1000

ror = ror.assign(**technologies['ror'])[ror['capacity'] > 0].dropna()
ror['profile'] = ror['tech'] + '-' + ror['bus'] + '-profile'

ror_sequences = inflows[ror.index] * ror_shares[ror.index] / ror['capacity']
ror_sequences.columns = ror_sequences.columns.map(ror['profile'])

# phs
phs = pd.DataFrame(index=countries)
phs['type'], phs['tech'], phs['bus'], phs['loss'], phs['capacity'] = \
    'storage', \
    'phs', \
    phs.index.astype(str) + '-electricity', \
    0, \
    capacities.loc[phs.index, ' installed pumped hydro capacities [GW]'] * 1000

phs['storage_capacity'] = phs['capacity'] * 6  # Brown et al.
phs = phs.assign(**technologies['phs'])

# other hydro / reservoir
rsv = pd.DataFrame(index=countries)
rsv['type'], rsv['tech'], rsv['bus'], rsv['loss'], rsv['capacity'], rsv['storage_capacity'] = \
    'reservoir', \
    'reservoir', \
    rsv.index.astype(str) + '-electricity', \
    0, \
    (capacities.loc[rsv.index, ' installed hydro capacities [GW]'] -
    ror_shares[rsv.index] * capacities.loc[rsv.index, ' installed hydro capacities [GW]'] -
    capacities.loc[rsv.index, ' installed pumped hydro capacities [GW]']) * 1000, \
    capacities.loc[rsv.index, ' reservoir capacity [TWh]'] * 1e6  # to MWh

rsv = rsv.assign(**technologies['reservoir'])[rsv['capacity'] > 0].dropna()
rsv['profile'] = rsv['tech'] + '-' + rsv['bus'] + '-profile'

rsv_sequences = inflows[rsv.index] * (1 - ror_shares[rsv.index])
rsv_sequences.columns = rsv_sequences.columns.map(rsv['profile'])

# write sequences to different files for better automatic foreignKey handling
# in meta data
building.write_sequences(
    'reservoir_profile.csv', rsv_sequences.set_index(building.timeindex()))
building.write_sequences(
    'ror_profile.csv', ror_sequences.set_index(building.timeindex()))

filenames = ['ror.csv', 'phs.csv', 'reservoir.csv']

for fn, df in zip(filenames, [ror, phs, rsv]):
    df.index = df.index.astype(str) + '_' + df['tech']
    df['capacity_cost'] = df.apply(
        lambda x: annuity(float(x['capacity_cost']) * 1000,
                      float(x['lifetime']),
                      config['wacc']), axis=1)
    building.write_elements(fn, df)
