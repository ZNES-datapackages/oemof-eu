#
from datapackage import Package
import datetime

import os
import pandas as pd
import numpy as np
import logging
import json
# import oemof base classes to create energy system objects
import logging

from oemof.solph import EnergySystem, Model, Bus, Sink, constraints
from oemof.tools import logger

import oemof.outputlib as outlib
from renpass import options, cli
from renpass import postprocessing as pp
from datapackage_utilities import aggregation, building, processing



config = building.get_config()

temporal_resolution = config['temporal_resolution']
emission_limit = config['emission_limit']

time = {}

from oemof.network import Bus

# create results path
results_path = os.path.join('results', config['name'])
if not os.path.exists(results_path):
    os.makedirs(results_path)

# store used config file
with open(os.path.join(results_path, 'config.json'), 'w') as outfile:
    json.dump(config, outfile, indent=4)

# copy package either aggregated or the original one (only data!)
if  temporal_resolution > 1:
    logging.info("Aggregating for temporal aggregation ... ")
    path = aggregation.temporal_skip('datapackage.json',
                                     temporal_resolution,
                                     path=results_path) + '/'
else:
    path = ''
    processing.copy_datapackage(
        'datapackage.json',
        os.path.join(results_path, 'original_input'),
        subset='data')

cli.stopwatch()

system = Bus('system')
setattr(system, 'emission_limit', emission_limit)

es = EnergySystem.from_datapackage(
    path + 'datapackage.json',
    attributemap={},
    typemap=options.typemap)
es.add(system)
time['energysystem'] = cli.stopwatch()

m = Model(es)

# m.write(io_options={'symbolic_solver_labels': True})

constraints.emission_limit(m, limit=system.emission_limit)

m.receive_duals()

time['model'] = cli.stopwatch()

m.solve('gurobi')
time['solve'] = cli.stopwatch()

results = m.results()

################################################################################
# postprocessing write results
################################################################################




writer = pd.ExcelWriter(os.path.join(results_path, 'results.xlsx'))

buses = building.read_elements('bus.csv')

connection_results = pp.component_results(es, results).get('connection')

for b in buses.index:
    supply = pp.supply_results(results=results, es=es,
                               bus=[b],
                               types=['dispatchable', 'volatile', 'storage',
                                      'conversion', 'backpressure', 'reservoir',
                                      'extraction'])

    supply.columns = supply.columns.droplevel([1,   2])

    if connection_results is not None and \
        es.groups[b] in list(connection_results.columns.levels[0]):
        ex = connection_results.loc[:, (es.groups[b], slice(None), 'flow')].sum(axis=1)
        im = connection_results.loc[:, (slice(None), es.groups[b], 'flow')].sum(axis=1)

        supply['net_import'] =  im-ex

    supply.to_excel(writer, b)


demand = pp.demand_results(results=results, es=es, bus=buses.index)
demand.columns = demand.columns.droplevel([0, 2])
demand.to_excel(writer, 'load')

all = pp.bus_results(es,
                     results,
                     select='scalars',
                     aggregate=True)

all.name = 'value'
endogenous = all.reset_index()
endogenous['tech'] = [
    getattr(t, 'tech', np.nan) for t in all.index.get_level_values(0)]


d = dict()
for node in es.nodes:
    if not isinstance(node, (Bus, Sink)):
        if getattr(node, 'tech', config['investment_technologies'][0]) not in config['investment_technologies']:
            key = (node, [n for n in node.outputs.keys()][0], 'capacity', node.tech)
            d[key] = {'value': node.capacity}
exogenous = pd.DataFrame.from_dict(d, orient='index').dropna()
exogenous.index = exogenous.index.set_names(['from', 'to', 'type', 'tech'])

capacities = pd.concat([endogenous, exogenous.reset_index()]).groupby(['to', 'tech']).sum().unstack('to')
capacities.columns = capacities.columns.droplevel(0)
capacities.to_excel(writer, 'installed_capacities')


duals = pp.bus_results(es, results, aggregate=True).xs('duals', level=2, axis=1)
duals.columns = duals.columns.droplevel(1)
(duals.T / m.objective_weighting).T.to_excel(writer, 'shadow_prices')

pp.component_results(
     es, results, select='sequences')['excess'].to_excel(writer,
                                                         'excess_electricity')



meta_results = outlib.processing.meta_results(m)
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


pd.concat([outlib.views.node(results, b, multiindex=True).get('scalars')
          for b in buses.index]).to_excel(writer, 'oemof-scalars-endogenous')

for b in buses.index:
    outlib.views.node(results, b, multiindex=True)['sequences'].to_excel(
                                                        writer, b + 'oemof-seq')

writer.save()


time['postprocessing'] = cli.stopwatch()
