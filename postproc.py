from os import path
import re
import datetime
import os.path
import netCDF4 as nc
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Union, List
# from htcal_path import path_grdc_data, path_grdc_alloc
import htcal_path

htpath = htcal_path.get_paths()

def get_forcing_date(force) -> datetime:
    return datetime.datetime.strptime(re.findall(r"since\s+([\w\-]+)", force['time'].units)[0], '%Y-%m-%d')


def get_river_output(ncfile, grdc_id, date=None) -> pd.DataFrame:
    """
    date: y, m, d: same as IFYYYY, IFMM and IFDD
    """
    if date is None:
        date_begin = get_forcing_date(ncfile)
    else:
        date_begin = datetime.date(*date)
    date_begin += datetime.timedelta(days=1)
    #
    # print(f'calculate rivout for grdc: {grdc_id}')
    rivout = get_river_discharge_at_gauge(grdc_id, ncfile).data
    date_range = pd.date_range(start=date_begin, periods=len(rivout))
#    return pd.DataFrame(index=date_range, data={'riv_output': rivout})
    return pd.DataFrame({'date': date_range, 'riv_output': rivout})


def get_grdc_id(path_grdc_alloc, basin_nr) -> int:
    df = pd.read_csv(f"{path_grdc_alloc}/GRDC_selection_ufz_resol_basin_mapped_v2.1.csv")
    return df[df['basin_15min'] == basin_nr]['ID'].values[0]


def get_discharge(df_obs: pd.DataFrame, df_mod: pd.DataFrame,
                  date_begin=None, date_end=None) -> List[pd.Series]:
    """Returns a pair of observation and simulation for the basin
    at the appropriate slice of time

    Args:
        df_obs: dataframe of discharge observation
        df_mod: dataframe of discharge simulation
    Returns:
        pair of dataframes for observation and simulation
        the two should have the same start and end date
    """
    if date_begin is None:
        begin = df_mod['date'].iloc[0]
    else:
        pass
    if date_end is None:
        end = df_mod['date'].iloc[-1]
    else:
        pass
    #
    idx1_mod = df_mod[df_mod['date'] == begin].index[0]
    idx2_mod = df_mod[df_mod['date'] == end].index[0]
    #
    idx1_obs = df_obs[df_obs['date'] == begin].index[0]
    idx2_obs = df_obs[df_obs['date'] == end].index[0]
    return df_obs['discharge'].iloc[idx1_obs: idx2_obs + 1], df_mod['riv_output'].iloc[idx1_mod:idx2_mod + 1]


def kge(obs, sim, components=True):
    def __kge__(y_obs, y_mod, components=True) -> Union[list, float]:
        r = np.corrcoef(y_obs, y_mod)[0, 1]
        alpha = np.std(y_mod) / np.std(y_obs)
        beta = np.mean(y_mod) / np.mean(y_obs)
        if components:
            return 1. - np.sqrt((1 - r)**2 + (1 - beta)**2 + (1 - alpha)**2), r, alpha, beta
        else:
            return 1. - np.sqrt((1 - r)**2 + (1 - beta)**2 + (1 - alpha)**2)

    # mask invalid values before calling kge
    obs_valid = np.ma.masked_invalid(obs)
    sim_valid = np.ma.masked_invalid(sim)
    obs_positive = np.ma.array(obs,mask=(obs < 0.0))
    sim_positive = np.ma.array(sim,mask=(sim < 0.0))
    msk = (~obs_valid.mask & ~sim_valid.mask & ~obs_positive.mask & ~sim_positive.mask)
    obs_valid_pos = obs[msk]
    sim_valid_pos = sim[msk]
    return __kge__(obs_valid_pos, sim_valid_pos, components=components)


def calc_kge(df_obs, df_mod, date_begin=None, date_end=None) -> float:
    obs, mod = get_discharge(df_obs, df_mod, date_begin=None, date_end=None)
    return kge(np.array(obs), np.array(mod), False)


def check_grdc_is_valid(basin_id, date_b, date_e) -> bool:
    """checks if the station has valid measurements for a given date range
    
    check_grdc_is_valid(4999, (1952, 1, 1), (1953, 1, 10) -> False)
    """
    df = get_grdc_discharge(basin_id)
    date_begin = datetime.date(*date_b)
    date_end = datetime.date(*date_e)
    idx_b = df.query(f'date=={date_begin.strftime("%Y-%m-%d")}').index[0]
    idx_e = df.query(f'date=={date_end.strftime("%Y-%m-%d")}').index[0]
    return np.all(df.loc[idx_b: idx_e]['discharge'].values > -9999)


def find_station(glb_x, glb_y, ulc_lat, ulc_lon, res=0.25, debug=False) -> List[Union[int, None]]:
    if glb_x != -9999 and glb_y != -9999:
        offx = -(-179.875 - ulc_lon) / res
        offy = (89.875 - ulc_lat) / res
        # print('offset x: {}, y: {}'.format(offx, offy))
        x = int(glb_x - offx - 1)
        y = int(glb_y - offy - 1)
        if debug:
            print('Station found at x: {}, y: {}'.format(x, y))
        return x, y
    else:
        return None, None


def get_river_discharge_at_gauge(grdc_id, nc_file) -> nc.Dataset:
    x1, y1, x2, y2 = extract_river_gauge_location(grdc_id, nc_file)
    #
    out1 = nc_file['rivout'][:, y1, x1]
    if x2 is not None and y2 is not None:
        out2 = nc_file['rivout'][:, y2, x2]
    else:
        out2 = np.zeros_like(out1)
    #print(f'rivout of gauge: {grdc_id}')
    #print(out1 + out2)
    return out1 + out2    


def dates_are_continuous(df) -> bool:
    ords = set(df['date'].apply(lambda row: row.toordinal()).values)
    return len(ords) == max(ords) - min(ords) + 1


def extract_river_gauge_location(grdc_id, nc_file) -> List[int]:
    # grdc_id = get_grdc_id(htpath.path_grdc_alloc, basin_id)
    df = pd.read_csv(f"{htpath.path_grdc_alloc}/GRDC_alloc_15min.txt", sep="\s+")
    #
    ulc_lon = nc_file['lon'][...].min()  # upper left corner
    ulc_lat = nc_file['lat'][...].max()  # upper left corner
    #
    glb_x1 = df[df['ID'] == int(grdc_id)]['ix1'].values[0]
    glb_y1 = df[df['ID'] == int(grdc_id)]['iy1'].values[0]
    glb_x2 = df[df['ID'] == int(grdc_id)]['ix2'].values[0]
    glb_y2 = df[df['ID'] == int(grdc_id)]['iy2'].values[0]
    #
    x1, y1 = find_station(glb_x1, glb_y1, ulc_lat, ulc_lon)
    x2, y2 = find_station(glb_x2, glb_y2, ulc_lat, ulc_lon)
    return x1, y1, x2, y2


def get_grdc_discharge(grdc_id) -> pd.DataFrame:
    def get_line(line):
        i1, i2, i3, i4, i5, i6 = line.split()
        return([datetime.date(int(i1), int(i2), int(i3)), int(i4), int(i5), float(i6)])
        
    # grdc_id = get_grdc_id(htpath.path_grdc_alloc, grdc_id)
    
    # build a dataframe for query the date
    lines = open(f'{htpath.path_grdc_data}/{grdc_id}.day', 'r').readlines()[5:]
    lines_data = [get_line(line) for line in lines]

    df = pd.DataFrame(lines_data)
    df.columns = ['date', 'hour', 'minute', 'discharge']
    return df
