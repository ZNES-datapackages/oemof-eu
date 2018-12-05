
import datetime
import json
import logging
import numpy as np
import os
import pandas as pd

from datapackage import Package

from datapackage_utilities import aggregation, building, processing

from oemof.solph import EnergySystem, Model, Bus, Sink, constraints
from oemof.solph.components import GenericStorage
from oemof.tools import logger, economics
import oemof.outputlib as outlib

from renpass import options, cli
from renpass import postprocessing as pp


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
        os.path.abspath(os.path.join(results_path, 'original_input')),
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


# for i in es.nodes:
#     if getattr(i, 'tech', None) == 'pv':
#         setattr(i, 'capacity_cost', i.capacity_cost * 2)


time['model'] = cli.stopwatch()

m.solve('gurobi')

time['solve'] = cli.stopwatch()

results = m.results()

################################################################################
# postprocessing write results
################################################################################
writer = pd.ExcelWriter(os.path.join(results_path, 'results.xlsx'))

buses = [b.label for b in es.nodes if isinstance(b, Bus)]

connection_results = pp.component_results(es, results).get('connection')


for b in buses:
    supply = pp.supply_results(results=results, es=es, bus=[b])
    supply.columns = supply.columns.droplevel([1, 2])

    if connection_results is not None and es.groups[b] in list(connection_results.columns.levels[0]):
        ex = connection_results.loc[:, (es.groups[b], slice(None), 'flow')].sum(axis=1)
        im = connection_results.loc[:, (slice(None), es.groups[b], 'flow')].sum(axis=1)
        supply['net_import'] =  im-ex

    supply.to_excel(writer, 'supply-' + b)


all = pp.bus_results(es, results, select='scalars', aggregate=True)
all.name = 'value'
endogenous = all.reset_index()
endogenous['tech'] = [
    getattr(t, 'tech', np.nan) for t in all.index.get_level_values(0)]

d = dict()
for node in es.nodes:
    if not isinstance(node, (Bus, Sink)):
        if getattr(node, 'capacity', None) is not None:
            key = (node, [n for n in node.outputs.keys()][0], 'capacity', node.tech) # for oemof logic
            d[key] = {'value': node.capacity}
exogenous = pd.DataFrame.from_dict(d, orient='index').dropna()
exogenous.index = exogenous.index.set_names(['from', 'to', 'type', 'tech'])

capacities = pd.concat(
    [endogenous, exogenous.reset_index()]).groupby(['to', 'tech']).sum().unstack('to')
capacities.columns = capacities.columns.droplevel(0)
capacities.to_excel(writer, 'capacities')

demand = pp.demand_results(results=results, es=es, bus=buses)
demand.columns = demand.columns.droplevel([0, 2])
demand.to_excel(writer, 'load')

duals = pp.bus_results(es, results, aggregate=True).xs('duals', level=2, axis=1)
duals.columns = duals.columns.droplevel(1)
(duals.T / m.objective_weighting).T.to_excel(writer, 'shadow_prices')

excess = pp.component_results(es, results, select='sequences')['excess']
excess.columns = excess.columns.droplevel([1,2])
excess.to_excel(writer, 'excess')

filling_levels = outlib.views.node_weight_by_type(results, GenericStorage)
filling_levels.columns = filling_levels.columns.droplevel(1)
filling_levels.to_excel(writer, 'filling_levels')

writer.save()

time['postprocessing'] = cli.stopwatch()

modelstats = outlib.processing.meta_results(m)
modelstats.pop('solver')
modelstats['problem'].pop('Sense')
modelstats.update({'logged_time': time})
with open(os.path.join(results_path, 'modelstats.json'), 'w') as outfile:
    json.dump(modelstats, outfile, indent=4)


# summary ----------------------------------------------------------------------
if False:
    excess_share = excess.sum() / demand.sum().values

    supply_sum = pp.supply_results(results=results, es=es, bus=buses).apply(lambda x: x[x > 0].sum()).reset_index()
    supply_sum['from'] = supply_sum.apply(lambda x: x['from'].label.split('-')[1], axis=1)
    supply_sum.drop('type', axis=1, inplace=True)
    supply_sum = supply_sum.set_index(['from', 'to']).unstack('from') / 1e6 * config['temporal_resolution']
    supply_sum.columns  = supply_sum.columns.droplevel(0)

    from matplotlib import colors

    color_dict = {
         name: colors.to_rgb(color) for name, color in options.techcolor.items()}
    ax = capacities.T.plot(kind='bar',
                 stacked=True,
                 color=[color_dict.get(x, '#333333') for x in capacities.index])
    ax.set_xlabel('Countries')
    ax.set_ylabel('Capacities in GW')
    ax.set_title('Installed capacities per country')
