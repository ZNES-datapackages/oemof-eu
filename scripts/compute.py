#
from datapackage import Package
import pandas as pd
import numpy as np

from oemof.solph import EnergySystem, Model
from oemof.outputlib import processing, views
from renpass import options, cli
from renpass import postprocessing as pp
from datapackage_utilities import aggregation, building

import pprint

test = True

time = {}

if test:
    print("Clustering for temporal aggregation ... ")
    path = aggregation.temporal_clustering('datapackage.json', 5, path='/tmp', how='daily') + '/'
else:
    path = ''

cli.stopwatch()

es = EnergySystem.from_datapackage(
    path + 'datapackage.json',
    attributemap={},
    typemap=options.typemap)
time['energysystem'] = cli.stopwatch()

m = Model(es, objective_weighting=es.temporal['weighting'])
time['model'] = cli.stopwatch()

m.solve('gurobi')
time['solve'] = cli.stopwatch()

results = m.results()

################################################################################
# postprocessing write results
################################################################################
buses = building.read_elements('bus.csv')

connection_results = pp.component_results(es, results)['connection']

writer = pd.ExcelWriter('results.xlsx')

for b in buses.index:
    supply = pp.supply_results(results=results, es=es,
                               bus=[b],
                               types=['dispatchable', 'volatile', 'storage'])

    supply.columns = supply.columns.droplevel([1,2])

    ex = connection_results.loc[:, (es.groups[b], slice(None), 'flow')].sum(axis=1)
    im = connection_results.loc[:, (slice(None), es.groups[b], 'flow')].sum(axis=1)

    supply['net_import'] =  ex-im

    supply.to_excel(writer, b)


demand = pp.demand_results(results=results, es=es, bus=buses.index)
demand.columns = demand.columns.droplevel([0,2])
demand.to_excel(writer, 'demand')

all = pp.bus_results(es,
                     results,
                     select='scalars',
                     aggregate=True)

all.name = 'value'
endogenous = all.reset_index()
endogenous['tech'] = [
    getattr(t, 'tech', np.nan) for t in all.index.get_level_values(0)]

inputs = processing.param_results(es)
d = dict()
for node, attr in inputs.items():
    if attr['scalars'].get('capacity') is not None:
        key = (node[0],
               [n for n in node[0].outputs.keys()][0], 'capacity',
               node[0].tech)
        d[key] = {'value': attr['scalars']['capacity']}
exogenous = pd.DataFrame.from_dict(d, orient='index').dropna()
exogenous.index = exogenous.index.set_names(['from', 'to', 'type', 'tech'])


capacities = pd.concat([endogenous, exogenous.reset_index()]).groupby(['to', 'tech']).sum().unstack('to')
capacities.columns = capacities.columns.droplevel(0)

capacities.to_excel(writer, 'installed_capacities')



#
# def transform_index(df):
#     """
#     """
#     new_df = df.reset_index()
#     new_df['tech'] = [
#         getattr(t, 'tech', np.nan) for t in df.index.get_level_values(0)]
#     new_df.set_index(['from', 'to', 'type', 'tech'], inplace=True)
#
#     return new_df
#
# transform_index(df=supply.T).groupby('tech').sum().T

#system_constraints.co2_limit(m, 100, ignore=['battery', 'pumped_storage', 'link'])

#
input_scalars = pd.concat([
    views.node(
        processing.parameter_as_dict(es),
        es.groups[b],
        multiindex=True)['scalars']
    for b in buses.index])

input_scalars.unstack('type').to_excel(writer, 'input_scalars')
writer.save()
