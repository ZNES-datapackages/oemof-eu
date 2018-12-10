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

if config['grid']['capacity'] == 2050:
    print('Using 2050 grid ...')
    import future_grid
elif config['grid']['capacity'] == 'SQ':
    print('Using existing grid ...')
    import status_quo_grid
else:
    print('No grid ... ')

print('Building electricity generation technologies ... ')
import electricity_generation

print('Building existing technologies ... ')
import hydro_generation

print('Building wind profiles ... ')
import capacity_factors_wind

print('Building pv profiles ... ')
import capacity_factors_pv

print('Building excess components ... ')
import electricity_excess

if config['heating']:
    print("Including heat component ... ")

    import decentral_heat_generation

    import central_heat_generation

    import heat_load

# add meta data from data using datapackage utils
building.infer_metadata(package_name='oemof-eu',
                        foreign_keys={
                            'bus': ['volatile', 'dispatchable', 'storage',
                                    'heat_storage', 'load', 'ror', 'reservoir',
                                    'phs', 'excess', 'boiler', 'commodity'],
                            'profile': ['load', 'volatile', 'heat_load', 'ror',
                                        'reservoir'],
                            'from_to_bus': ['link', 'conversion', 'line'],
                            'chp': ['backpressure', 'extraction']
                            }
                        )
