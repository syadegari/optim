from postproc import *
import os
import re
import pandas as pd
import argparse

def get__multiyear_dirs(path):
    return [x for x in os.listdir(path) if os.path.isdir(f'{path}/{x}') if re.match('\d{4}', x)]


def kge_multiyear(basin_nr, basin_path, warmup):
    os.chdir(f"{basin_path}/run")
    sim_folders = [int(x) for x in get__multiyear_dirs('.')]
    sim_folders.sort()
    rivouts = []
    for year in sim_folders:
        rivouts.append(get_river_output(nc.Dataset(f"{year}/o_rivout_cmf.nc"), basin_nr))
        rivout_concat = pd.concat(rivouts).reset_index()
        obs, mod = get_discharge(
            get_grdc_discharge(basin_nr),
            rivout_concat
        )
        kge_val = kge(obs[warmup : ], mod[warmup : ])
    return kge_val

usage_example="""
The basin structure should look like the following

/data/htcal/data/debug_optim/8smallbasins_default/basin_6144/runs/sim_33/
.
└── basin_6144
    ├── mpr
    └── run
        ├── 1999
        ├── 2000
        ├── 2001
        ├── 2002
        ├── 2003
        ├── 2004
        ├── 2005
        ├── 2006
        ├── 2007
        └── 2008

important things to have is a basin folder (in this case basin_6144)
with a `run` directory underneath it and inside this folder
the multiyear runs should be stored

python kge_multiyear.py -p /data/htcal/data/debug_optim/8smallbasins_default/basin_6144/runs/sim_33/basin_6144 -w 180 -n 6144
"""

parser = argparse.ArgumentParser(description="KGE output for multiyear runs",
                                 epilog=usage_example,
                                 formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-n', '--basin_number', type=int,
                    help="basin number (a four digit integer)")
parser.add_argument('-w', '--warmup', type=int  ,
                    help="warmup days")
parser.add_argument('-p', '--path', type=str,
                    help='path to the basin where multiyear runs are stored')
args = parser.parse_args()
print(args)

# print(kge_multiyear(6144, "/data/htcal/data/debug_optim/8smallbasins_default/basin_6144/runs/sim_33/basin_6144", 180))
print(kge_multiyear(args.basin_number, args.path, args.warmup))
