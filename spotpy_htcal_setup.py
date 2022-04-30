import spotpy
import numpy as np
import pandas as pd
import netCDF4 as nc
#
import ntpath
import sys
import os
import os.path
import re
import shutil
import socket
import datetime
#
from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
import f90nml as nml
#
from pathlib import Path
from subprocess import Popen
from postproc import *
import mpi4py.futures as futures
from penalty import calculate_penalty_error
#
from lutreader import basin_lut

DEBUG = False


# path -+
#       |-> run/ [sim_1, sim_2, ...] +
#                                    |-> [basin_1, basin_2, ...]
# path/run/sim_13/basin_4999

def get_dir(path):
    return [x for x in os.listdir(path) if os.path.isdir(f'{path}/{x}')]


def write_params_file(sim_path, x):
    fh = open(f'{sim_path}/parameters.dat', 'w')
    for param_name, param_val in zip(x.name, [val for val in x]):
        fh.write(f"{param_name} = {param_val}\n")
    fh.close()


def create_basin_run_directory(path_root, path_sim, run_dirs):
    """
    copies the default simulation into the sim folder
    works for basins and stations
    """
    for run_dir in run_dirs:
        shutil.copytree(f"{path_root}/default_sim/{run_dir}",
                        f"{path_sim}/{run_dir}", symlinks=True)


def modify_basin_with_new_params(sim_path, run_ids, run_dirs, control_file, x):
    '''
    modifies all the input files under sim_n (n ∈ ℕ)
    we need to do that for each basin and in each basin change the mpr
    and all the simulation years

    test_run/
    ├── default_sim
    │   ├── basin_3269
    │   │   ├── mpr
    │   │   └── run
    │   │       ├── 1999
    │   │       └── 2000
    │   └── basin_6333
    │       ├── mpr
    │       └── run
    │           ├── 1999
    │           └── 2000
    ├── __pycache__
    └── runs
    └── sim_1      <=== sim_path (you are here!)
        ├── basin_3269
        │   ├── mpr
        │   └── run
        │       ├── 1999
        │       └── 2000
        └── basin_6333
            ├── mpr
            └── run
                ├── 1999
                └── 2000
'''
    for ii, run_id in enumerate(run_ids):
        run_dir = run_dirs[ii]
        # open the htessel in the sim_path
        # change to basin directory
        parent_dir = os.getcwd()
        os.chdir(f"{sim_path}/{run_dir}")
        # we open mpr and htessel files
        year_range = range(control_file.training[run_id]['year_begin'],
                           control_file.training[run_id]['year_end'] + 1)
        htessel_inputs = [HTESSELNameList(nml.read(f"run/{year}/input"))\
                          for year in year_range]
        mpr = MPRNameList(nml.read("mpr/mpr_global_parameter.nml"))
        for ht_input, year in zip(htessel_inputs, year_range):
            
            ht_input.read_only = False
            mpr.read_only = False
            # modify_forcing_path(htessel, sim_path, run_id)
            modify_params(ht_input, mpr, dict(zip(x.name, [v for v in x])))
            special_treatments(ht_input)
            ht_input.read_only = True
            mpr.read_only = True
            # write the changes
            ht_input.write(f"./run/{year}")
            mpr.write("./mpr")
        # change to parent directory
        os.chdir(parent_dir)


def modify_params(htessel, mpr, params_dict):
    for k, v in params_dict.items():
        # if k == 'zach_thetar_1':
        #     import pdb; pdb.set_trace()
        if k in htessel.get_all_model_parameters():
            htessel[k] = v
        elif k in mpr.get_all_model_parameters():
            mpr[k] = v
        else:
            raise Exception(f'{k}, {v} pair was not found')

# def modify_htessel_params(htessel, params_dict):
#     for k, v in params_dict.items():
#         if k in htessel.get_all_model_parameters():
#             htessel[k] = v
# 
# def modify_mpr_params(mpr, params_dict):
#     for k, v in params_dict.items():
#         if k in mpr.get_all_model_parameters():
#             mpr[k] = v

def special_treatments(nmlist):
    if nmlist.tag == 'input':
        nmlist['rez0ice'] = int(nmlist['rez0ice'])
    return nmlist


def remove_all_but_last_sim(run_folder):
    sim_nums = [int(re.match("sim_(\d+)", f)[1]) for f in os.listdir(run_folder) if f.find('sim_')!=-1]
    sim_nums = sorted(sim_nums)
    if sim_nums == []:
        exit('At least one simulation should exist in runs folder!')
    if len(sim_nums) > 1:
        for sim_num in sim_nums[:-1]:
            shutil.rmtree(f"{run_folder}/sim_{sim_num}")

def mpi_debug(name):
    print('----------')
    print(f'executing {name}' )
    print(f'executing on machine {socket.gethostname()}')
    print(f'threads available: {os.environ["OMP_NUM_THREADS"]}')
    print(f'time of executation: {datetime.datetime.now().strftime("%H:%M:%S")}')
    print(f'in directory {os.getcwd()}')
    print('----------')


def run_htessel_jobs(path_sim):
    if DEBUG:
        mpi_debug('before HTESSEL')
    out, err = Popen('./run_htessel',
                     shell=True,
                     cwd=path_sim).communicate()
    if DEBUG:
        mpi_debug('after HTESSEL')


def run_mpr_jobs(path_sim):
    if DEBUG:
        mpi_debug('before MPR')
    out, err = Popen('./run_mpr',
                     shell=True,
                     cwd=path_sim).communicate()
    if DEBUG:
        mpi_debug('after MPR')


class spot_setup_htcal(object):
    #
    def __init__(self, control_file, restart:bool, clean_completed:bool,
                 nthreads:int, basin_lookup = 'basin_lut.org'):
        # import the control file
        control_file_path, control_file = ntpath.split(control_file)
        sys.path.insert(0, control_file_path)
        control_file = __import__(control_file)
        print(f"\nUsing control file: {control_file}\n")
        print(f"\nUsing basin lut: {basin_lookup}\n")
        #
        self.restart = restart
        self.control_file_path = control_file_path
        self.control_file = control_file 
        self.params = []
        for param_name, param_values in self.control_file.params.items():
            lower, upper, defulat = param_values
            self.params.append(spotpy.parameter.Uniform(param_name,
                                                        np.array(lower),
                                                        np.array(upper)))

        cf_key_ids = self.control_file.training.keys()
        if len(cf_key_ids) == 1:
            blut = basin_lut(basin_lookup)
            bid, gid = blut.get_ids(list(cf_key_ids)[0])
            if gid is not None:
                self.run_ids = [gid]
                self.run_dirs = [f"station_{gid}"]
                self.grdc   = [gid]
                self.basins = [bid]
            else:
                self.run_ids = [bid]
                self.run_dirs = [f"basin_{bid}"]
                self.grdc = self.control_file.training[bid]['grdc_ids']
                for ii, _ in enumerate(self.grdc):
                    self.grdc[ii] = str(self.grdc[ii])
                self.basins = [bid]
        else:
            self.run_ids = cf_key_ids
            self.run_dirs = [f"station_{ii}" for ii in cf_key_ids]
            self.grdc   = []
            self.basins = []
            for basin in self.run_ids:
                self.grdc.extend(self.control_file.training[basin]['grdc_ids'])
                self.basins.extend([basin for i in range(len(self.control_file.training[basin]['grdc_ids']))])
            for ii, _ in enumerate(self.grdc):
                self.grdc[ii] = str(self.grdc[ii])
        # prepare
        self.create_run_directory(self.control_file_path)
        self.nthreads = nthreads
        self.rm_sim_folder = clean_completed

    def create_run_directory(self, path):
        if not self.restart:
            assert not os.path.isdir(f"{path}/runs"), f"runs directory exists."        
            Path(f'{path}/runs').mkdir(exist_ok=True)

    def create_param_run_directory(self, path):
        # get all the simulation direcotories
        sim_folders = [f'{path}/runs/{x}' for x in get_dir(f'{path}/runs') if x.find('sim_') != -1]    

        if sim_folders == []:
            sim_number = 1
        else:
            # get the last sim folder
            sim_number = max([int(re.findall(r".+sim_(\d+)", x)[0]) for x in sim_folders]) + 1

        Path(f'{path}/runs/sim_{sim_number}').mkdir()
        return f'{path}/runs/sim_{sim_number}'

        
    def parameters(self):
        return spotpy.parameter.generate(self.params)


    def simulation(self, x):
        # TODO: replace this after fixing the csv-file problem
        with open(f"{self.control_file_path}/runs/res.txt", 'a') as res_file:
            print("parameters: ", [_ for _ in x], file=res_file)
        print("parameters: ", [_ for _ in x])
        #
        sim_path = self.create_param_run_directory(self.control_file_path)
        write_params_file(sim_path, x)
        create_basin_run_directory(self.control_file_path, sim_path, self.run_dirs)
        modify_basin_with_new_params(sim_path, self.run_ids, self.run_dirs, self.control_file, x)

        paths = [f'{sim_path}/{run_dir}' for run_dir in self.run_dirs]

        print('running mpr jobs with CommExec ...')
        print(paths)
        # run mpr jobs
        with futures.MPIPoolExecutor() as executor:
            _ = executor.map(run_mpr_jobs, paths)
        #  check the penalties for each variable specified in `penalty` dict
        run_htessel = False
        try:
            penalty_errors = calculate_penalty_error(self.run_dirs,
                                                     self.control_file.penalty,
                                                     sim_path)
            if not np.isclose(np.array([v for _, v in penalty_errors.items()]).sum(),
                              0.0, atol=1e-8):
                for run_dir in self.run_dirs:
                    shutil.rmtree(f'{sim_path}/{run_dir}/run')
                print('mprin thresholds violated, skipping htessel run')
                print(penalty_errors)
                return penalty_errors
            else:
                run_htessel = True
        except AttributeError:
            print('no penalty formulation is found, running htessel')
            run_htessel = True
        # run programs. Only run htessel if
        #                         1- No penalty exists in the control
        #                         2- When penalty exist, run when no penalty term is activated
        # run htessel jobs
        if run_htessel:
            with futures.MPICommExecutor() as executor:
                _ = executor.map(run_htessel_jobs, paths)
            results = {}
            for ii, run_id in enumerate(self.run_ids):
                run_dir = self.run_dirs[ii]
                # print(f'Getting rivout for basin: {basin_nr}')
                year_range = range(self.control_file.training[run_id]['year_begin'],
                                   self.control_file.training[run_id]['year_end'] + 1)
                # for grdc_id in self.control_file.training[basin_nr]['grdc_ids']:
                # TODO: HERE WE NEED A FIX, ELSE NO MULTIBASIN WILL RUN
                for grdc_id in self.grdc:
                    # print(f'    grdc_no: {grdc_id}')
                    rivouts = []
                    for year in year_range:
                        rivouts.append(get_river_output(nc.Dataset(f"{sim_path}/{run_dir}/run/{year}/o_rivout_cmf.nc"), grdc_id))
                    # print(rivouts)
                    results[str(grdc_id)] = rivouts
            # concat the restuls before sending back
            # print(results)
            return {
                str(grdc_id): pd.concat(results[str(grdc_id)]).reset_index() for grdc_id in self.grdc
            }
            

    def objectivefunction(self, simulation, evaluation):
        # get a key from the simulation
        k = list(simulation.keys())[0]
        if isinstance(simulation[k], float):
            # penalty formulation since we have a dict with floats
            # for htessel runs we return {basin_nr: pandas.Series} object
            with open(f"{self.control_file_path}/runs/res.txt", 'a') as res_file:
                res_file.write(f"{simulation}\n")
            #
            if self.rm_sim_folder:
                remove_all_but_last_sim(f"{self.control_file_path}/runs")
            return -15 + sum(list(simulation.values()))
        else:
            sim_folders = [f'{self.control_file_path}/runs/{x}' \
                           for x in get_dir(f'{self.control_file_path}/runs') if x.find('sim_') != -1]
            sim_number = max([int(re.findall(r".+sim_(\d+)", x)[0]) for x in sim_folders])
            kges = {}
            for ii, grdc_id in enumerate(self.grdc):
                obs, mod = get_discharge(evaluation[grdc_id], simulation[grdc_id])
                warmup = self.control_file.training[self.run_ids[ii]]['warmup']
                # import pdb; pdb.set_trace()
                kges[grdc_id] = kge(obs[warmup : ], mod[warmup : ], components=True)
            # compute all the components of kge and write them into log but only return the kge itself
            kge_means = np.array(list(kges.values())).mean(axis=0)
            print(f"kge: {kge_means}")
            with open(f"{self.control_file_path}/runs/res.txt", 'a') as res_file:
                res_file.write(f"{kge_means}\n")
            if self.rm_sim_folder:
                remove_all_but_last_sim(f"{self.control_file_path}/runs")
            if np.nan in kge_means:
                exit('Aborting the optimizer. Nan has been encountered in KGE results')
            return kge_means[0]


    def evaluation(self):
        return {
            grdc_id : get_grdc_discharge(grdc_id) for grdc_id in self.grdc
        }

# setup = spot_setup_htcal("/p/home/jusers/yadegarivarnamkhasti1/juwels/project/build/optim/self.control_file.py")
