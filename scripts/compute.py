
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

time['model'] = cli.stopwatch()

m.solve('gurobi')

time['solve'] = cli.stopwatch()

results = m.results()

################################################################################
# postprocessing write results
################################################################################
#writer = pd.ExcelWriter(os.path.join(results_path, 'results.xlsx'))

def save(df, name, how='csv', writer=None):
    if how == 'excel':
        df.to_excel(writer, name)
    if how == 'csv':
        df.to_csv(os.path.join(results_path, name + '.csv'))

buses = [b.label for b in es.nodes if isinstance(b, Bus)]

# line_results = pp.line_results(es, results, select='sequences')
# if line_results is not None:
#     line_results.to_excel(writer, 'lines')
#
# line_capacities = pp.line_results(es, results, select='scalars')
# if line_capacities is not None:
#     line_capacities.T.to_excel(writer, 'line_capacities')

link_results = pp.component_results(es, results).get('link')
if link_results is not None:
    save(link_results, 'links-oemof')

imports = pd.DataFrame()
for b in buses:
    supply = pp.supply_results(results=results, es=es, bus=[b])
    supply.columns = supply.columns.droplevel([1, 2])

    if link_results is not None and es.groups[b] in list(link_results.columns.levels[0]):
        ex = link_results.loc[:, (es.groups[b], slice(None), 'flow')].sum(axis=1)
        im = link_results.loc[:, (slice(None), es.groups[b], 'flow')].sum(axis=1)

        net_import =  im-ex
        net_import.name = es.groups[b]
        imports = pd.concat([imports, net_import], axis=1)

        supply['import'] = net_import

    save(supply, 'supply-' + b)
    save(imports, 'imports')


all = pp.bus_results(es, results, select='scalars', aggregate=True)
all.name = 'value'
endogenous = all.reset_index()
endogenous['tech'] = [
    getattr(t, 'tech', np.nan) for t in all.index.get_level_values(0)]


d = dict()
for node in es.nodes:
    if not isinstance(node, (Bus, Sink)):
        if getattr(node, 'capacity', None) is not None:
            if isinstance(node, options.typemap['link']):
                pass #key = (node.input, node.output, 'capacity', node.tech) # for oemof logic
            else:
                key = (node, [n for n in node.outputs.keys()][0], 'capacity', node.tech) # for oemof logic
                d[key] = {'value': node.capacity}
exogenous = pd.DataFrame.from_dict(d, orient='index').dropna()
exogenous.index = exogenous.index.set_names(['from', 'to', 'type', 'tech'])

capacities = pd.concat(
    [endogenous, exogenous.reset_index()]).groupby(['to', 'tech']).sum().unstack('to')
capacities.columns = capacities.columns.droplevel(0)
save(capacities, 'capacities')

demand = pp.demand_results(results=results, es=es, bus=buses)
demand.columns = demand.columns.droplevel([0, 2])
save(demand, 'load')

duals = pp.bus_results(es, results, aggregate=True).xs('duals', level=2, axis=1)
duals.columns = duals.columns.droplevel(1)
duals = (duals.T / m.objective_weighting).T
save(duals, 'shadow_prices')

excess = pp.component_results(es, results, select='sequences')['excess']
excess.columns = excess.columns.droplevel([1,2])
save(excess, 'excess')

filling_levels = outlib.views.node_weight_by_type(results, GenericStorage)
filling_levels.columns = filling_levels.columns.droplevel(1)
save(filling_levels, 'filling_levels')

#writer.save()

time['postprocessing'] = cli.stopwatch()

modelstats = outlib.processing.meta_results(m)
modelstats.pop('solver')
modelstats['problem'].pop('Sense')
modelstats.update({'logged_time': time})
with open(os.path.join(results_path, 'modelstats.json'), 'w') as outfile:
    json.dump(modelstats, outfile, indent=4)


# summary ----------------------------------------------------------------------
if True:
    supply_sum = pp.supply_results(
        results=results, es=es, bus=buses, types=[
            'dispatchable', 'volatile', 'conversion', 'backpressure', 'extraction',
            'reservoir']).sum().reset_index() #.apply(lambda x: x[x > 0].sum())
    supply_sum['from'] = supply_sum.apply(lambda x: x['from'].label.split('-')[1], axis=1)
    supply_sum.drop('type', axis=1, inplace=True)
    supply_sum = (supply_sum.set_index(['from', 'to']).unstack('from') /
                  1e6 * config['temporal_resolution'])
    supply_sum.columns  = supply_sum.columns.droplevel(0)

    excess_share = (excess.sum() * config['temporal_resolution'] / 1e6) / supply_sum.sum(axis=1)
    excess_share.name = 'excess'

    summary = pd.concat([supply_sum, excess_share], axis=1)

    save(summary, 'summary')
