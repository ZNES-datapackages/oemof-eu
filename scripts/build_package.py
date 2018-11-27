from datapackage_utilities import building, processing

# clean directories to avoid errors
processing.clean_datapackage(directories=['data', 'resources'])

# get config file
config = building.get_config()

# initialize directories etc. based on config file
building.initialize_dpkg()

# run scripts to add data
print('Building buses ... ')
import bus

print('Building electricity load and profiles ...')
import electricity_load

if config['optimize_grid']:
    print('Using optimized grid ...')
    import optimized_grid
else:
    print('Using existing grid ...')
    import status_quo_grid

print('Building electricity generation technologies ... ')
import electricity_generation

print('Building existing technologies ... ')
import existing_generation

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

if config['include_heating']:
    print("Including heat component ... ")

    import decentral_heat_generation

    import central_heat_generation

    import heat_load

# add meta data from data using datapackage utils
building.infer_metadata(package_name='angus_base_scenario',
                        foreign_keys={
                            'bus': ['volatile', 'dispatchable', 'storage',
                                    'heat_storage',
                                    'load', 'run_of_river', 'reservoir',
                                    'pumped_storage', 'excess', 'boiler'],
                            'profile': ['load', 'volatile', 'run_of_river',
                                        'heat_load'],
                            'from_to_bus': ['connection', 'conversion'],
                            'chp': ['backpressure', 'extraction']
                            }
                        )
