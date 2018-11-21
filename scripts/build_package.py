from datapackage_utilities import building, processing

# clean directories to avoid errors
processing.clean_datapackage(directories=['data', 'resources', 'cache'])

# get config file
config = building.get_config()

# initialize directories etc. based on config file
building.initialize_dpkg()

# run scripts to add data
print('Building buses ... ')
import electricity_buses

print('Building electricity load and profiles ...')
import electricity_load

print('Building grid ...')
import grid

print('Building generation technologies ... ')
import generation

print('Building storage technologies ... ')
import storage

print('Building existing technologies ... ')
import existing_technologies

print('Building hydro profiles ... ')
import run_of_river_profiles

print('Building hydro parameters ... ')
import hydro_edge_parameters

print('Building wind profiles ... ')
import capacity_factors_wind

print('Building pv profiles ... ')
import capacity_factors_pv

print('Building excess components ... ')
import electricity_excess

# print('Building heat components ... ')
#import district_heating

# add meta data from data using datapackage utils
building.infer_metadata(package_name='angus_base_scenario',
                        foreign_keys={
                            'bus': ['volatile', 'dispatchable', 'storage',
                                    'heat_storage', 'heat_load',
                                    'load', 'run_of_river', 'reservoir',
                                    'pumped_storage', 'excess', 'boiler'],
                            'profile': ['load', 'volatile', 'run_of_river',
                                        'heat_load'],
                            'from_to_bus': ['grid', 'power_to_heat'],
                            'chp': ['backpressure', 'extraction']
                            }
                        )
