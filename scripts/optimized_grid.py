# -*- coding: utf-8 -*-
"""
"""
import json
import os
import re

import pandas as pd

from datapackage_utilities import building

def create_resource(path):
    from datapackage import Resource
    resource = Resource({'path': path})
    resource.infer()
    resource.descriptor['schema']['primaryKey'] = 'name'
    resource.descriptor['description'] = 'Installed transmission capacities from the e-highway 2050 scenario'
    resource.descriptor['title'] = 'Installed transmission capacities'
    resource.descriptor['sources'] = [{
        'title': 'E-Highway 2050 transmission capacities',
        'path': 'http://www.e-highway2050.eu/fileadmin/documents/' +
                'Results/e-Highway_database_per_country-08022016.xlsx'}]

    resource.descriptor['schema']['foreignKeys'] =   [
        {
            "fields": "from_bus",
            "reference": {
                "resource": "bus",
                "fields": "name"}},
        {
            "fields": "to_bus",
            "reference": {
                "resource": "bus",
                "fields": "name"}}]


    resource.commit()

    if resource.valid:
        resource.save('resources/'+ resource.name + '.json')



# helper function for transshipment
def remove_links(row):
    """ Takes a row of the dataframe and returns True if the
    link is within the country.
    """
    r = row.split('-')
    if r[0].split('_')[1].strip() == r[1].split('_')[1].strip():
        return False
    else:
        return True

config = building.get_config()

filename = 'e-Highway_database_per_country-08022016.xlsx'

filepath = os.path.join('archive', filename)

if os.path.exists(filepath):
    # if file exist in archive use this file
    df_2030 = pd.read_excel(filepath, sheet_name='T93', index_col=[1],
                            skiprows=[0, 1, 3]).fillna(0)

    df_2050 = pd.read_excel(filepath, sheet_name='T94', index_col=[1],
                            skiprows=[0, 1, 3]).fillna(0)
else:
    # if file does not exist, try to download and check if valid xlsx file
    logging.info('File for e-Highway capacities does not exist. Download..')
    filepath = building.download_data(
        'http://www.e-highway2050.eu/fileadmin/documents/'  +
        filename)
    try:
        book = open_workbook(filepath)
        df_2030 = pd.read_excel(filepath, sheet_name='T93', index_col=[1],
                                skiprows=[0, 1, 3]).fillna(0)

        df_2050 = pd.read_excel(filepath, sheet_name='T94', index_col=[1],
                                skiprows=[0, 1, 3]).fillna(0)
    except XLRDError as e:
        raise XLRDError('Downloaded file not valid xlsx file.')

def _prepare_frame(df):
    """ prepare dataframe
    """
    df.dropna(how='all', axis=1, inplace=True)
    df.drop(df.tail(1).index, inplace=True)
    df.reset_index(inplace=True)
    df['Links'] = df['Links'].apply(lambda row: row.upper())

    # remove all links inside countries
    df = df.loc[df['Links'].apply(remove_links)]

    # strip down to letters only for grouping
    df['Links'] = df['Links'].apply(lambda row: re.sub(r'[^a-zA-Z]+', '', row))


    df = df.groupby(df['Links']).sum()

    df.reset_index(inplace=True)

    df = pd.concat([
        pd.DataFrame(df['Links'].apply(lambda row: [row[0:2], row[2:4]]).tolist(),
                    columns=['from', 'to']),
                    df], axis=1)
    return df

df_2050 = _prepare_frame(df_2050).set_index(['Links'])
df_2030  = _prepare_frame(df_2030).set_index(['Links'])



# sum 2030 + additional capacities 2050
df = df_2030.copy()

scenario = '100% RES'


elements = {}
for _, row in df_2030.iterrows():
    if row['from'] in config['regions'] and \
        row['to'] in config['regions']:
        predecessor = row['from'] + '-electricity'
        successor = row['to'] + '-electricity'
        element_name = predecessor + '-' + successor

        element = {
            'type': 'connection',
            'loss': 0.03,
            'from_bus': predecessor,
            'to_bus': successor,
            #'capacity': row[scenario],
            'capacity_cost': row['Length'] * 400, # €/MWkm
            'length': row['Length']}

        elements[element_name] = element

path = building.write_elements('connection.csv',
                                pd.DataFrame.from_dict(elements, orient='index'))

#create_resource(path)
