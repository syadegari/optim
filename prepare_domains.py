import sys
import ntpath
import shutil
import glob
import re
from htessel_namelist import HTESSELNameList
from cama_namelist import CamaNameList
import f90nml as nml
import netCDF4 as nc
import os
import subprocess as sp
import argparse

eve_run_cmd="""#!/bin/bash

module purge
module load foss/2019b
module load netCDF-Fortran
./MPR-*

module purge
module load foss/2018b
module load grib_api
module load netCDF-Fortran

./master1s.exe
"""

juwels_run_cmd="""
"""

def get_forcing_file_single(y1, y2):
    assert y1 < y2
    if y1 + 1 == y2:
        return str(y1)
    else:
        return f"{str(y1)}_{str(y2-1)}"


def get_forcing_files(cf, basin_id):
    if cf.forcing_files == 'single':
        year_begin = cf.training[basin_id]['year_begin']
        year_end   = cf.training[basin_id]['year_end']
        return get_forcing_file_single(year_begin, year_end)
    else:
        raise Exception


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--control-file', 
    help="control file")
args = parser.parse_args()
# control_file_path = "/p/home/jusers/yadegarivarnamkhasti1/juwels/project/build/EEE/examples/mpr-htessel/agu_runs/control_file"
control_file_path, _ = os.path.splitext(args.control_file)
assert os.path.isfile(f"{control_file_path}.py"),\
    f"Control file {control_file_path}.py was not found"


control_file_path, _ = os.path.splitext(args.control_file)
cf_path, cf_file = ntpath.split(control_file_path)
sys.path.insert(0, cf_path)
control_file = __import__(cf_file)
cf = control_file

# get direcotry of the control file
path, _ = ntpath.split(cf.__file__)
os.chdir(path)
mpr_exe = glob.glob(f'{cf.path_execs}/mpr/{cf.mpr_tf}/MPR-*')[0]
htessel_exe = glob.glob(f'{cf.path_execs}/master1s*')[0]


"""
Some overall notes on what is used and how things are organized for development only

Repositories:
mprpy
mpr 
htessel
ecfpy

Data:
forcing
static
GRDC
soilgrid


default_sim/{basins}
iter_1/{basins}
iter_2/{basins}

mpr -> symlink
mpr.nml -> symlink
master1s -> symlink
mpr_global -> copy
input -> copy
input_cmf -> copy
soil params -> symlink

forcings -> path in the input
"""
# default_sim: this contains all the basins specified in the domain
os.makedirs("default_sim")
os.chdir("default_sim")
# make directories for each basin
for basin_id in cf.training:
    basin_path = f"basin_{basin_id}"
    os.makedirs(basin_path)
    os.chdir(f"basin_{basin_id}")

    # copy cama and htessel input files
    print(os.getcwd())
    shutil.copyfile("../../input", "input")
    shutil.copyfile("../../input_cmf.nam", "input_cmf.nam")

    # copy executables and mpr files
    shutil.copy(f"{cf.path_execs}/master1s.exe", f"master1s.exe")
    shutil.copy(glob.glob(f"{cf.path_execs}/mpr/{cf.mpr_tf}/MPR-*")[0], ntpath.split(glob.glob(f"{cf.path_execs}/mpr/{cf.mpr_tf}/MPR-*")[0])[1])
    shutil.copyfile(f"{cf.path_execs}/mpr/{cf.mpr_tf}/mpr.nml", f"mpr.nml")
    shutil.copyfile(f"{cf.path_execs}/mpr/{cf.mpr_tf}/mpr_global_parameter.nml", f"mpr_global_parameter.nml")

    # soil symlinks
    os.symlink("surfclim", "surfclim.nc")
    os.symlink("mprin.nc", "mprin")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/BLDFIE_M.nc", "BLDFIE_M.nc")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/SNDPPT_M.nc", "SNDPPT_M.nc")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/CLYPPT_M.nc", "CLYPPT_M.nc")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/ORCDRC_M.nc", "ORCDRC_M.nc")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/SLTPPT_M.nc", "SLTPPT_M.nc")
    os.symlink(f"{cf.path_soilgrid}/basin_{basin_id}/TEXMHT_M.nc", "TEXMHT_M.nc")

    #
    # copy the static files
    #
    for f in glob.glob(f"{cf.path_static}/basin_{basin_id}/*"):
        _, file_name = ntpath.split(f)
        shutil.copyfile(f, f"{file_name}")
    #
    # create diminfo.txt file
    #
    cama_clips = [int(x) for x in open('cdo_clip_cama.txt').readlines()[0].split(',')]
    htessel_clips = [int(x) for x in  open('cdo_clip_htessel.txt').readlines()[0].split(',')]
    #
    nx = cama_clips[1] - cama_clips[0] + 1
    ny = cama_clips[3] - cama_clips[2] + 1
    nlfp = nc.Dataset('rivclim.nc')['lev'].shape[0]    
    nxin = htessel_clips[1] - htessel_clips[0] + 1
    nyin = htessel_clips[3] - htessel_clips[2] + 1
    inpn = nc.Dataset('inpmat.nc')['lev'].shape[0]
    #
    with open('diminfo.txt', 'w') as fh:
        for val in [nx, ny, nlfp, nxin, nyin, inpn, "NONE", 0, 0, 0, 0]:
            fh.write(f"{str(val)}\n")
    #


    # modify forcing information in input files
    forcing_name_years = get_forcing_files(cf, basin_id)
    
    # modify forcing path ... set to absolute path
    cama = CamaNameList(nml.read('input_cmf.nam'))
    htessel = HTESSELNameList(nml.read('input'))

    # first modify htessel
    htessel.read_only = False
    for forcing in ["CFORCLW", "CFORCP", "CFORCQ",
                    "CFORCRAIN", "CFORCSNOW", "CFORCSW",
                    "CFORCT", "CFORCU"]:
        _, force_name = ntpath.split(htessel[forcing])
        force_name = re.findall("(.+?)_", force_name)[0]
        htessel[forcing] = f"{cf.path_forcing}/basin_{basin_id}/{force_name}_{forcing_name_years}.nc"
    #
    
    # change the timing and dates in htessel and cama input files
    htessel['IFYYYY'] = cf.training[basin_id]['year_begin']
    htessel['IFMM'] = 1
    htessel['IFDD'] = 1
    htessel['IFTIM'] = 0
    #
    # we need one of the forcing files for the dimension
    ncfile = nc.Dataset(f"{cf.path_forcing}/basin_{basin_id}/Tair_{forcing_name_years}.nc")
    #
    htessel['NINDAT'] = int(f"{cf.training[basin_id]['year_begin']}{htessel['IFMM']:02}{htessel['IFDD']:02}")
    #
    htessel['NSTART'] = 0
    htessel['NSTOP'] = ncfile['time'].shape[0] - 1
    #
    htessel['NDFORC'] = ncfile['time'].shape[0]
    htessel['NLAT'] = ncfile['lat'].shape[0]
    htessel['NLON'] = ncfile['lon'].shape[0]
    htessel.read_only = True
    htessel.write()

    # now the cama file
    cama.read_only = False
    #
    cama['SDAYIN'] = 1
    cama['SHOURIN'] = 0
    cama['SMONIN'] = 1
    cama['SYEARIN'] = cf.training[basin_id]['year_begin'] 
    #
    cama['SDAY'] = 1
    cama['SHOUR'] = 0
    cama['SMON'] = 1
    cama['SYEAR'] = cf.training[basin_id]['year_begin'] 
    #    
    cama['EDAY'] = 1
    cama['EHOUR'] = 0
    cama['EMON'] = 1
    cama['EYEAR'] = cf.training[basin_id]['year_end'] 
    #
    cama.readonly = True
    cama.write()

    # run script
    open('run_programs', 'w').write(eve_run_cmd)
    sp.Popen("chmod u+x run_programs", shell=True).communicate()
    
    os.chdir("..")


