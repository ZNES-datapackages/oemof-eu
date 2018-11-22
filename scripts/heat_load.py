
district_heat_demand = {
    'district-heat-demand-DE': {
        'type': 'load',
        'bus': 'DE-heat',
        'amount': 190 * 1e6, # 190.000.000 MWh i.e. 190 TWh
        'profile': 'district-heat-demand-DE-profile'}}

path = building.write_elements(
    'load.csv',
    pd.DataFrame.from_dict(district_heat_demand, orient='index'))

heat_demand_profile = pd.Series(
    data=pd.read_csv('archive/thermal_load_profile.csv', sep=";")['thermal_load'].values,
    index=pd.date_range(str(config['year']), periods=8760, freq='H'))
heat_demand_profile.rename('district-heat-demand-DE-profile', inplace=True)

path = building.write_sequences('load_profile.csv', heat_demand_profile)
