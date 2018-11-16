#
from datapackage import Package
import datetime

import pandas as pd
import numpy as np
import logging

# import oemof base classes to create energy system objects
import logging

from oemof.solph import EnergySystem, Model, constraints
from oemof.tools import logger

from oemof.outputlib import processing, views
from renpass import options, cli
from renpass import postprocessing as pp
from datapackage_utilities import aggregation, building


aggregate = True
emission_limit = 250*1e6 * 0.2
time = {}


if aggregate:
    logging.info("Aggregating for temporal aggregation ... ")
    path = aggregation.temporal_skip('datapackage.json', 3, path='/tmp') + '/'
else:
    path = ''

cli.stopwatch()

es = EnergySystem.from_datapackage(
    path + 'datapackage.json',
    attributemap={},
    typemap=options.typemap)
time['energysystem'] = cli.stopwatch()

m = Model(es)

constraints.emission_limit(m, limit=emission_limit)

m.receive_duals()

time['model'] = cli.stopwatch()

m.solve('gurobi')
time['solve'] = cli.stopwatch()

results = m.results()


################################################################################
# postprocessing write results
################################################################################
buses = building.read_elements('bus.csv')

connection_results = pp.component_results(es, results).get('connection')

writer = pd.ExcelWriter(
            datetime.datetime.now().strftime("%Y%m%d_%H:%M") + '_results.xlsx')

for b in buses.index:
    supply = pp.supply_results(results=results, es=es,
                               bus=[b],
                               types=['dispatchable', 'volatile', 'storage'])

    supply.columns = supply.columns.droplevel([1,   2])

    if connection_results is not None:
        ex = connection_results.loc[:, (es.groups[b], slice(None), 'flow')].sum(axis=1)
        im = connection_results.loc[:, (slice(None), es.groups[b], 'flow')].sum(axis=1)

        supply['net_import'] =  im-ex

    supply.to_excel(writer, b)


# import matplotlib.pyplot as plt
# fig = plt.Figure(figsize=(20, 10))
# ax = supply.reset_index(drop=True).loc[0:48].plot(kind='bar', stacked=True)
# ax.legend(loc='upper center', bbox_to_anchor=(1.45, 0.8), shadow=True, ncol=2)
# demand.loc[:, es.groups['DE_load']].reset_index(drop=True).loc[0:48].plot()
# plt.savefig('plot.pdf')


demand = pp.demand_results(results=results, es=es, bus=buses.index)
demand.columns = demand.columns.droplevel([0, 2])
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


duals = pp.bus_results(es, results, aggregate=True).xs('duals', level=2, axis=1)
duals.columns = duals.columns.droplevel(1)
(duals.T / m.objective_weighting).T.to_excel(writer, 'shadow_prices')

#(duals.T / m.objective_weighting).T.mean()
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


pp.component_results(
    es, results, select='sequences')['excess'].to_excel(writer,
                                                        'excess_electricity')


input_scalars = pd.concat([
    views.node(
        processing.parameter_as_dict(es),
        es.groups[b],
        multiindex=True)['scalars']
    for b in buses.index])

input_scalars.unstack('type').to_excel(writer, 'input_scalars')

time['postprocessing'] = cli.stopwatch()

meta_results = processing.meta_results(m)
pd.DataFrame({
    'time': time,
    'objective': {
        m.name: meta_results['objective']},
    'solver_time': {
        m.name: meta_results['solver']['Time']},
    'constraints': {
        m.name: meta_results['problem']['Number of constraints']},
    'variables': {
        m.name: meta_results['problem']['Number of variables']}})\
            .to_excel(writer, 'meta_results')


pd.concat([views.node(results, b, multiindex=True)['scalars'] for b in buses.index]).to_excel(writer, 'scalar_view')
for b in buses.index:
    views.node(results, b, multiindex=True)['sequences'].to_excel(writer, b+'-seq')

writer.save()

m.total_emissions()
#supply.sum()/demand.sum().values
