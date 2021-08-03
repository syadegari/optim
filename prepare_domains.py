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
from numpy import mod
import argparse
import htcal_path
import lutreader

# all the global paths we need
htpath = htcal_path.get_paths()

def run_command(cf, run_id, dir_names):
    # hostname = os.uname()[1]
    #
    try:
        if 'mlail_scaling' in cf.params or 'mlaih_scaling' in cf.params:
            has_LAI_param = True
        else:
            has_LAI_param = False
    except NameError:
        has_LAI_param = False
    run_cmd = htcal_path.runcommand(has_LAI_param=has_LAI_param)
    #
    hostname = 'frontend1'
    if hostname in ['datascience1', 'frontend1', 'frontend2']:
        # print('    Hostsystem: eve')
        run_cmd_mpr = run_cmd.mpr.format(
            dir_name=dir_names['mpr']
        )
        run_cmd_htessel = run_cmd.htessel.format(
            year_begin=cf.training[run_id]['year_begin'],
            year_end=cf.training[run_id]['year_end'],
            dir_name=dir_names['model_run']
        )
    return(run_cmd_mpr, run_cmd_htessel)

class basin_setup():
    def __init__(self, syear, cf, htpath, basin_id):
        # read cama and htessel sp. info
        cama_clips    = [int(x) for x in open(f"{htpath.path_static}/basin_{basin_id}/cdo_clip_cama.txt").readlines()[0].split(',')]
        htessel_clips = [int(x) for x in open(f"{htpath.path_static}/basin_{basin_id}/cdo_clip_htessel.txt").readlines()[0].split(',')]
        #
        self.cama_nx      = cama_clips[1] - cama_clips[0] + 1
        self.cama_ny      = cama_clips[3] - cama_clips[2] + 1
        self.cama_nlfp    = nc.Dataset(f"{htpath.path_static}/basin_{basin_id}/rivclim.nc")['lev'].shape[0]
        self.htessel_nx   = htessel_clips[1] - htessel_clips[0] + 1
        self.htessel_ny   = htessel_clips[3] - htessel_clips[2] + 1
        self.htessel_inpn = nc.Dataset(f"{htpath.path_static}/basin_{basin_id}/inpmat.nc")['lev'].shape[0]

        self.current_year = syear
        self.syear        = syear

        self.htessel_nstart = 0
        if mod(syear, 4) == 0:
            self.htessel_nstop  = 8784
        else:
            self.htessel_nstop  = 8760

    def write_diminfo(self, path):
        with open(f"{path}/diminfo.txt", 'w') as fh:
            for val in [self.cama_nx, self.cama_ny, self.cama_nlfp, self.htessel_nx,
                        self.htessel_ny, self.htessel_inpn, "NONE", 0, 0, 0, 0]:
                fh.write(f"{str(val)}\n")

    def next_leg(self):
        self.current_year += 1
        self.htessel_nstart = self.htessel_nstop
        if mod(self.current_year, 4) == 0:
            self.htessel_nstop  += 8784
        else:
            self.htessel_nstop  += 8760

def setup_mpr(cf, htpath, basin_id, grdc_id, run_path, dir_names):
    mpr_path = os.path.join(run_path, dir_names['mpr'])
    os.makedirs(mpr_path)
    # executable
    # shutil.copy(glob.glob(f"{htpath.path_execs}/mpr/{cf.mpr_tf}/MPR-*")[0], ntpath.split(glob.glob(f"{htpath.path_execs}/mpr/{cf.mpr_tf}/mpr")[0])[1])
    shutil.copy(glob.glob(f"{htpath.path_execs}/mpr/{cf.mpr_tf}/MPR-*")[0], f"{mpr_path}/mpr")
    # namelists
    shutil.copyfile(f"{htpath.path_execs}/mpr/{cf.mpr_tf}/mpr.nml", f"{mpr_path}/mpr.nml")
    shutil.copyfile(f"{htpath.path_execs}/mpr/{cf.mpr_tf}/mpr_global_parameter.nml", f"{mpr_path}/mpr_global_parameter.nml")
    # input
    if grdc_id is not None and os.path.isdir(f"{htpath.path_soilgrid}/station_{grdc_id}"):
            mpr_data_in_dir = f"{htpath.path_soilgrid}/station_{grdc_id}"
            shutil.copyfile(f"{mpr_data_in_dir}/surfclim", f"{mpr_path}/surfclim")
    else:
            mpr_data_in_dir = f"{htpath.path_soilgrid}/basin_{basin_id}"
            shutil.copyfile(f"{htpath.path_static}/basin_{basin_id}/surfclim",
                            f"{mpr_path}/surfclim")
    for soil_filename in ["BLDFIE_M.nc", "SNDPPT_M.nc", "CLYPPT_M.nc",
                          "ORCDRC_M.nc", "SLTPPT_M.nc", "TEXMHT_M.nc"]:
            os.symlink(f"{mpr_data_in_dir}/{soil_filename}", f"{mpr_path}/{soil_filename}")


def setup_htessel(cf, htpath, basin_id, grdc_id, run_path, dir_names):
    if grdc_id is not None:
        run_id = grdc_id
    else:
        run_id = basin_id
    year_begin = cf.training[run_id]['year_begin']
    year_end   = cf.training[run_id]['year_end']
    b_setup = basin_setup(year_begin, cf, htpath, basin_id)
    # diminfo file
    b_setup.write_diminfo(run_path)
    for yy in range(year_begin, year_end + 1):
        # print(f'        setting up year {yy}')
        _setup_htessel_yy_dir(b_setup, cf, htpath, basin_id, grdc_id, run_path, dir_names, yy, init = yy == year_begin)
        _update_htessel_nml(b_setup, cf, htpath, basin_id, run_path, dir_names, yy, init = yy == year_begin)
        _update_cama_nml(b_setup, cf, htpath, basin_id, run_path, dir_names, yy, init = yy == year_begin)
        b_setup.next_leg()

def _setup_htessel_yy_dir(b_setup, cf, htpath, basin_id, grdc_id, run_path, dir_names, yy, init = True):
    yy_path = os.path.join(run_path, dir_names['model_run'], str(yy))
    mpr_path = os.path.join(run_path, dir_names['mpr'])
    if grdc_id is not None:
        data_dir = f"station_{grdc_id}"
    else:
        data_dir = f"basin_{basin_id}"
    # print(f'        preparing directory: {yy_path}')
    os.makedirs(yy_path)
    # executable
    shutil.copy(f"{htpath.path_execs}/master1s.exe", f"{yy_path}/htessel")
    # namelists
    shutil.copyfile(f"{htpath.path_misc}/input_htessel", f"{yy_path}/input")
    shutil.copyfile(f"{htpath.path_misc}/input_cmf.nam", f"{yy_path}/input_cmf.nam")
    # input htessel
    os.symlink(f"../../mpr/surfclim", f"{yy_path}/surfclim")
    os.symlink(f"../../mpr/mprin", f"{yy_path}/mprin")
    if init:
        os.symlink(f"{htpath.path_static}/{data_dir}/soilinit", f"{yy_path}/soilinit")
    else:
        prev_yy = str(yy - 1)
        os.symlink(f"../{prev_yy}/restartout.nc", f"{yy_path}/restartin.nc")
        # TODO: here is a critical part if the legs are not annual but e.g. monthly
        os.symlink(f"../{prev_yy}/restart{yy}010100.nc", f"{yy_path}/restartcmf.nc")
    # input cama
    for ff in [ 'rivpar.nc', 'rivclim.nc', 'inpmat.nc' ]:
        os.symlink(f"{htpath.path_static}/{data_dir}/{ff}", f"{yy_path}/{ff}")
    # diminfo
    os.symlink(f"{run_path}/diminfo.txt", f"{yy_path}/diminfo.txt")

def _update_htessel_nml(b_setup, cf, htpath, basin_id, run_path, dir_names, yy, init = True):
    yy_path = os.path.join(run_path, dir_names['model_run'], str(yy))
    htessel = HTESSELNameList(nml.read(f"{yy_path}/input"))

    htessel.read_only = False
    for forcing in ["CFORCLW", "CFORCP", "CFORCQ",
                    "CFORCRAIN", "CFORCSNOW", "CFORCSW",
                    "CFORCT", "CFORCU"]:
        _, force_name = ntpath.split(htessel[forcing])
        force_name = re.findall("(.+?)_", force_name)[0]
        htessel[forcing] = f"{htpath.path_forcing}/basin_{basin_id}/{force_name}_{yy}.nc"

    # start or restart
    htessel['LNF'] = init
    # change the timing and dates in htessel and cama input files
    htessel['IFYYYY'] = b_setup.current_year - 1
    htessel['IFMM'] = 12
    htessel['IFDD'] = 31
    htessel['IFTIM'] = 1800

    htessel['NINDAT'] = int(str(b_setup.syear) + '0101')
    #
    htessel['NSTART'] = b_setup.htessel_nstart
    htessel['NSTOP'] = b_setup.htessel_nstop
    #
    htessel['NDFORC'] = 8790
    htessel['NLAT'] = b_setup.htessel_ny

    htessel['NLON'] = b_setup.htessel_nx
    htessel.read_only = True
    htessel.write(f"{yy_path}")

def _update_cama_nml(b_setup, cf, htpath, basin_id, run_path, dir_names, yy, init = True):
    yy_path = os.path.join(run_path, dir_names['model_run'], str(yy))
    cama = CamaNameList(nml.read(f"{yy_path}/input_cmf.nam"))
    # now the cama file
    cama.read_only = False
    # restart
    cama['LRESTART'] = not init
    #
    cama['SDAYIN'] = 1
    cama['SHOURIN'] = 0
    cama['SMONIN'] = 1
    cama['SYEARIN'] = b_setup.current_year
    #
    cama['SDAY'] = 1
    cama['SHOUR'] = 0
    cama['SMON'] = 1
    cama['SYEAR'] = b_setup.current_year
    #    
    cama['EDAY'] = 1
    cama['EHOUR'] = 0
    cama['EMON'] = 1
    cama['EYEAR'] = b_setup.current_year + 1
    #
    cama.readonly = True
    cama.write(f"{yy_path}")

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--control-file', 
    help="control file")
parser.add_argument('-l', '--basin_lut', dest = 'basin_lut', default = 'basin_lut.org',
    help = "basin lut")
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

basin_lut = lutreader.basin_lut(args.basin_lut)

# get direcotry of the control file
path, _ = ntpath.split(cf.__file__)
os.chdir(path)
mpr_exe = glob.glob(f'{htpath.path_execs}/mpr/{cf.mpr_tf}/MPR-*')[0]
htessel_exe = glob.glob(f'{htpath.path_execs}/master1s*')[0]

# some path settings
dir_names = {'mpr' : 'mpr',
             'model_run' : 'run'}

# default_sim: this contains all the basins specified in the domain
os.makedirs("default_sim")
os.chdir("default_sim")
exp_basedir = os.getcwd()
# make directories for each basin
for training_id in cf.training:
    basin_id, grdc_id = basin_lut.get_ids(training_id)
    if grdc_id is None:
        run_id = str(basin_id)
        run_dir = f"basin_{basin_id}"
    else:
        run_id = str(grdc_id)
        run_dir = f"station_{grdc_id}"
    # create basin dir
    print(f'Setting up default sim directories for basin {basin_id} in:')
    run_path = os.path.join(exp_basedir, run_dir)
    print(run_path)
    os.makedirs(run_path)
    os.chdir(run_path)

    # mpr
    print(f'    preparing mpr ...')
    setup_mpr(cf, htpath, basin_id, grdc_id, run_path, dir_names)

    # htessel
    print(f'    preparing htessel ...')
    setup_htessel(cf, htpath, basin_id, grdc_id, run_path, dir_names)

    # run script
    print(f'    writing run script ...')
    run_command(cf, run_id, dir_names)
    run_cmd_mpr, run_cmd_htessel = run_command(cf, run_id, dir_names)
    open(os.path.join(run_path, 'run_mpr'), 'w').write(run_cmd_mpr)
    open(os.path.join(run_path, 'run_htessel'), 'w').write(run_cmd_htessel)
    sp.Popen("chmod u+x run_mpr", shell=True).communicate()
    sp.Popen("chmod u+x run_htessel", shell=True).communicate()

    os.chdir(exp_basedir)

    print(f'    done!')


