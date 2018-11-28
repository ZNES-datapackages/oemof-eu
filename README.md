# Datapackage for ANGUS Base Scenario

# General description

The model is based on the Open Energy Modelling Framework (oemof). It used
classes from the [oemof-tabular](https://github.com/oemof/oemof-tabular) package
to build the model.

The model optimizes dispatch and investment of supply and storage
for one year in a hourly resolution for the following countries: LU, NL, DK,
SE, PL, CZ, AT, NO, BE, FR, CH, DE.


# Model input data

All model input data is provided in a datapackage. In this datapackage all
scripts to process input data are also provided.

## Supply

* Wind offshore, wind onshore and pv energy potentials per country have been
  based on a recent study from Brown et al. and are found in the
  [technology-potential](https://github.com/ZNES-datapackages/technology-potential) datapackage.
* Hourly capacity factors for wind and pv are based on  [renewables     ninja](https://www.renewables.ninja/downloads). The datasets used of current
  installed capacities. Therefore these values are likely to be conservative
  with regard to energy production from these technologies.  
* Biomass / gas is neglected in as a carrier for supply of electricity or heat as
  it is assumed to be used in the transport sector.
* For hydro run of river and reservoir are considered. As there is only
  limited potential for new hydro capacities theses are
  assumed to be current capacities. Profiles for inflow has been based on
  results of the [restore2050](https://zenodo.org/record/804244) project.
* Conventional technologies considered are Open Cycle Gasturbines,
  Closed Cycle Gas Turbines and Coal fired powerplants.

## Demand

* Electricity demand profiles are generated from the [OPSD](https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_singleindex.csv) project.
* Total energy demand for 2050 is based on [ehighway](http://www.e-highway2050.eu/fileadmin/documents/Results/e-Highway_database_per_country-08022016.xlsx) scenarios.

## Storage and Grid

* Existing pumped hydro storage capacities are condsidered in the model
* The grid is fixed and not subject to optimization and based on the [ehighway](http://www.e-highway2050.eu/fileadmin/documents/Results/e-Highway_database_per_country-08022016.xlsx) scenarios.
* Batteries can be installed without a restricted technical potential
* CAES Potential per country has been derived from ZNES-scenario.

## Heat

...



## Costs

* Input data costs and technology information are provided in
[technology-cost](https://github.com/ZNES-datapackages/technology-cost) datapackage.
* Annuity for capital costs has been calculated with 0.07 interest rate
