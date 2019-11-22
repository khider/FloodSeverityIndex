#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 13:57:38 2019

@author: deborahkhider

Calculate flood sevrity index based on volumetric flow threshold.
Returns one file for every  year.
"""

import xarray as xr
import numpy as np
import glob as glob
from datetime import date
import sys
import ast

def openDatasets(data,thresholds,year,bounding_box):
    '''Open the thresholds and GloFAS datasets for the appropriate year

    Args:
        data (str): path to GloFAS in netcdf format. Data needs to be oragnized in yearly folders
        thresholds (str): Name of the netcdf file containing the thresholds data
        year (list): year to consider
        bounding_box (list): min_lon, max_lon, min_lat, max_lat

    Returns:
        val (numpy array): Q values cut to the bounding box
        Q2 (numpy array): Threshold Q for a 2-yr flood
        Q5 (numpy array): Theshold Q for a 5-yr flood
        Q20 (numpy array): Threshold Q for a 20-yr flood
        lat (numpy array): latitude vector
        lon (numpy array): longitude vector
        time (numpy array): time vector
    '''
    # path + folders
    path = data+'/'+str(year)
    nc_files = (glob.glob(path+'/*.nc'))
    file_names=[]
    for file in nc_files:
        file_names.append(file)
    file_names.sort()
    #open
    data = xr.open_mfdataset(file_names)
    p_ = data.sel(lat=slice(bounding_box[3], bounding_box[2]),\
                  lon=slice(bounding_box[0],bounding_box[1]))
    val = p_.dis24.values

    #open thresholds
    thres = xr.open_dataset(thresholds)
    t_ = thres.sel(lat=slice(bounding_box[3], bounding_box[2]),\
                  lon=slice(bounding_box[0],bounding_box[1]))
    Q5 = t_['Q_5'].values
    Q2 = t_['Q_2'].values
    Q20 = t_['Q_20'].values

    lat = p_['lat'].values
    lon = p_['lon'].values
    time = p_['time'].values

    return val, Q2, Q5, Q20, lat, lon, time

def calculateIndex(val, Q2, Q5, Q20, lat, lon, time):
    '''Calculate a flooding index based on threshold levels

    The flooding index is boolean. 1: medium flood (2-yr retrun period ),
    2: high (5-yr retrun period) and 3: severe (20-yr return period)

    Args:
       val (numpy array): Q values cut to the bounding box
       Q2 (numpy array): Threshold Q for a 2-yr flood
       Q5 (numpy array): Theshold Q for a 5-yr flood
       Q20 (numpy array): Threshold Q for a 20-yr flood
       lat (numpy array): latitude vector
       lon (numpy array): longitude vector
       time (numpy array): time vector

    Returns:
        flood_bool (numpy array): the boolean index for flood severity

    '''
# put a boolean for flood level, 0: no flood, 1: Q2, 2: Q5, 3: Q20
    flood_bool = np.zeros(np.shape(val))

    for idx_time, i_time in enumerate(time):
        for idx_lat, i_lat in enumerate(lat):
            for idx_lon, i_lon in enumerate(lon):
                if val[idx_time,idx_lat,idx_lon]>=Q20[idx_lat,idx_lon]:
                    flood_bool[idx_time,idx_lat,idx_lon]= 3
                elif val[idx_time,idx_lat,idx_lon]<Q2[idx_lat,idx_lon]:
                    flood_bool[idx_time,idx_lat,idx_lon] = 0
                elif val[idx_time,idx_lat,idx_lon]>=Q2[idx_lat,idx_lon] and val[idx_time,idx_lat,idx_lon]<Q5[idx_lat,idx_lon]:
                    flood_bool[idx_time,idx_lat,idx_lon] = 1
                elif val[idx_time,idx_lat,idx_lon]>=Q5[idx_lat,idx_lon] and val[idx_time,idx_lat,idx_lon]<Q20[idx_lat,idx_lon]:
                    flood_bool[idx_time,idx_lat,idx_lon] = 2
                elif np.isnan(val[idx_time,idx_lat,idx_lon]):
                    flood_bool[idx_time,idx_lat,idx_lon] = np.nan

    return flood_bool

def writeNetcdf(flood_bool, lat, lon, time, year):
    ''' Write netcdf with the flooding index

    Args:
        flood_bool (numpy array): Boolean arrays containing the flood severity index
        lat (numpy array): Vector of latitudes
        lon (numpy array): Vector of longtidues
        time (numpy array): Vector of time
        year (int): year of interest
    '''
    #write as a data array
    da_flood = xr.DataArray(flood_bool,coords=[time,lat,lon],dims=['time','lat','lon'])
    da_flood.attrs['title'] = 'Flood level Severity (medium, high, and severe)'
    da_flood.attrs['long_name'] = 'Flood Level Severity'
    da_flood.attrs['units'] = 'unitless'
    da_flood.attrs['valid_min'] = 0
    da_flood.attrs['valid_max'] = 3
    da_flood.attrs['missing_value'] = np.nan
    da_flood.attrs['standard_name'] = 'channel_water_flow__flood_volume-flux_severity_index'

    ds = da_flood.to_dataset(name='flood')
    ds.attrs['title'] = "Flood Severity"
    ds.attrs['summary'] = 'Flood severity index: medium (2-yr flood, index=1),'+\
        'high (5-yr flood, index=2), and severe (20-yr flood, index=3), inferred from'+\
        'the GloFAS dataset. Thresholds were determined by fitting a Gumbel extreme'+\
        ' value distribution to the yearly maxima in each grid cell over 1981-2017.'
    ds.attrs['date_created'] = str(date.today())
    ds.attrs['creator_name'] = 'Deborah Khider'
    ds.attrs['creator_email'] = 'khider@usc.edu'
    ds.attrs['institution'] = 'USC Information Sciences Institute'
    ds.attrs['geospatial_lat_min'] = np.min(lat)
    ds.attrs['geospatial_lat_max'] = np.max(lat)
    ds.attrs['geospatial_lon_min'] = np.min(lon)
    ds.attrs['geospatial_lon_max'] = np.max(lon)
    ds.attrs['time_coverage_start'] = str(ds.time.values[0])
    ds.attrs['time_coverage_end'] = str(ds.time.values[-1])
    ds.attrs['time_coverage_resolution'] = 'daily'

    ds.to_netcdf('GloFAS_FloodIndex_'+str(year)+'.nc')

if __name__ == "__main__":
    #params
    bounding_box = ast.literal_eval(sys.argv[3])
    year = ast.literal_eval(sys.argv[4])
    thresholds = sys.argv[2]
    data = sys.argv[1]

    #Run the functions in a row
    for y in year:
        val, Q2, Q5, Q20, lat, lon, time = openDatasets(data,thresholds,y,bounding_box)
        flood_bool = calculateIndex(val, Q2, Q5, Q20, lat, lon, time)
        writeNetcdf(flood_bool, lat, lon, time, y)
