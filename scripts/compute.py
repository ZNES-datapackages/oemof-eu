#
from datapackage import Package

from oemof.solph import EnergySystem, Model
from renpass import options, system_constraints, renpass
from datapackage_utilities import aggregation

import pprint

test = False

time = {}

if test:
    path = aggregation.temporal_clustering('datapackage.json', 3, path='/tmp', how='daily') + '/'
else:
    path = ''

renpass.stopwatch()

es = EnergySystem.from_datapackage(
    path + 'datapackage.json',
    attributemap={},
    typemap=options.typemap)
time['energysystem'] = renpass.stopwatch()

es._typemap = options.typemap

m = Model(es) #objective_weighting=es.temporal['weighting']
time['model'] = renpass.stopwatch()

m.solve('gurobi')
time['solve'] = renpass.stopwatch()


#m.write('model.lp', io_options={'symbolic_solver_labels': True})
renpass.write_results(es, m, Package(path + 'datapackage.json'),
                      **{
                    '--output-directory':'results',
                    '--output-orient': 'component'})
time['write_results'] = renpass.stopwatch()


#system_constraints.co2_limit(m, 100, ignore=['battery', 'pumped_storage', 'link'])
