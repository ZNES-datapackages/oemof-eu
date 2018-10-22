#
from datapackage import Package

from oemof.solph import EnergySystem, Model
from renpass import options, renpass, postprocessing
from datapackage_utilities import aggregation, building

import pprint

test = True

time = {}

if test:
    print("Clustering for temporal aggregation ... ")
    path = aggregation.temporal_clustering('datapackage.json', 15, path='/tmp', how='daily') + '/'
else:
    path = ''

renpass.stopwatch()

es = EnergySystem.from_datapackage(
    path + 'datapackage.json',
    attributemap={},
    typemap=options.typemap)
time['energysystem'] = renpass.stopwatch()

es._typemap = options.typemap

m = Model(es, objective_weighting=es.temporal['weighting'])
time['model'] = renpass.stopwatch()

m.solve('gurobi')
time['solve'] = renpass.stopwatch()


if False:
	m.write('model.lp', io_options={'symbolic_solver_labels': True})

renpass.write_results(es, m, Package(path + 'datapackage.json'),
                      **{
                    '--output-directory':'results-component',
                    '--output-orient': 'component'})

renpass.write_results(es, m, Package(path + 'datapackage.json'),
                      **{
                    '--output-directory':'results-bus',
                    '--output-orient': 'bus'})

postprocessing.connection_net_results(
    'results-component/angus_base_scenario__temporal_cluster__daily_15/sequences/connection.csv',
    hubs=[b + '-electricity' for b in building.get_config()['buses']])

postprocessing.storage_net_results(
    'results-component/angus_base_scenario__temporal_cluster__daily_15/sequences/storage.csv')

time['write_results'] = renpass.stopwatch()


#system_constraints.co2_limit(m, 100, ignore=['battery', 'pumped_storage', 'link'])
