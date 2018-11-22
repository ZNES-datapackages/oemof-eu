# -*- coding: utf-8 -*-
"""
"""
import logging
import json
import os
from xlrd import open_workbook, XLRDError

from datapackage import Package, Resource
import pandas as pd

from datapackage_utilities import building



# first we build the elements ---------------

config = building.get_config()

filename = 'e-Highway_database_per_country-08022016.xlsx'
filepath = os.path.join('archive', filename)

if config['year'] == 2050:
    sheet = 'T40'
if os.path.exists(filepath):
    df = pd.read_excel(filepath, sheet_name=sheet, index_col=[0])
else:
    logging.info('File for e-Highway loads does not exist. Trying to download..')
    filepath = building.download_data(
        'http://www.e-highway2050.eu/fileadmin/documents/Results/'  +
        filename)
    try:
        book = open_workbook(filepath)
        df = pd.read_excel(filepath, sheet_name=sheet, index_col=[0])
    except XLRDError as e:
        raise XLRDError('Downloaded file not valid xlsx file.')

df.set_index('Unnamed: 1', inplace=True)
df.drop(df.index[0:1], inplace=True)
df.dropna(how='all', axis=1, inplace=True)


elements = df.loc[config['regions'], df.loc['Scenario'] == '100% RES']


elements = elements.rename(columns = {'Unnamed: 3':'amount'})
elements.index.name = 'bus'
elements.reset_index(inplace=True)
elements['name'] = elements.apply(lambda row: row.bus + '_load', axis=1)
elements['profile'] = elements.apply(lambda row: row.bus + '_profile', axis=1)
elements['type'] = 'load'
elements['carrier'] = 'electricity'
elements.set_index('name', inplace=True)

elements.bus = [b + '-electricity' for b in elements.bus]

elements['amount'] = elements['amount'] * 1000 # to MWh
path = building.write_elements('load.csv', elements)


# now we are adding the sequences

filepath = building.download_data(
    'https://data.open-power-system-data.org/time_series/2017-07-09/' +
    'time_series_60min_singleindex.csv')

raw_data = pd.read_csv(filepath, index_col=[0], parse_dates=True)

suffix = '_load_old'

year = str(config['demand_year'])

countries = config['regions']

columns = [c + suffix for c in countries]

timeseries = raw_data[year][columns]

load_total = timeseries.sum()

load_profile = timeseries / load_total

sequences_df = pd.DataFrame(index=load_profile.index)
elements = building.read_elements('load.csv')
for c in countries:
    # get sequence name from elements edge_parameters (include re-exp to also
    # check for 'elec' or similar)
    sequence_name = elements.at[
            elements.index[elements.index.str.contains(c)][0],
            'profile']

    sequences_df[sequence_name] = load_profile[c + suffix].values

sequences_df.index = building.timeindex()

path = building.write_sequences('load_profile.csv', sequences_df)
