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

print('Building investment technologies ... ')
import technologies

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

# add meta data from data using datapackage utils
building.infer_metadata(package_name='angus_base_scenario',
                        foreign_keys={
                            'bus': ['volatile', 'dispatchable', 'storage',
                                    'load', 'run_of_river', 'reservoir',
                                    'pumped_storage', 'excess'],
                            'profile': ['load', 'volatile', 'run_of_river'],
                            'from_to_bus': ['grid']
                            }
                        )
