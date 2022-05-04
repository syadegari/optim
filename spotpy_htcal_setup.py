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
from collections import namedtuple
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


def modify_basin_with_new_params(sim_path, grdcs, x):
    '''
    modifies all the input files under sim_n (n ∈ ℕ)
    we need to do that for each basin and in each basin change the mpr
    and all the simulation years

    test_run/
    ├── default_sim
    │   ├── basin_3269
    │   │   ├── mpr
    │   │   └── run
    │   │       ├── 1999
    │   │       └── 2000
    │   └── basin_6333
    │       ├── mpr
    │       └── run
    │           ├── 1999
    │           └── 2000
    ├── __pycache__
    └── runs
    └── sim_1      <=== sim_path (you are here!)
        ├── basin_3269
        │   ├── mpr
        │   └── run
        │       ├── 1999
        │       └── 2000
        └── basin_6333
            ├── mpr
            └── run
                ├── 1999
                └── 2000
'''
    # import is here to prevent the clash with Path from pathlib
    from path import Path

    # looping on grdcs can be ineffiecient (in case of multi-stations
    # in a single basin, which is not supported at the moment) but still
    # correct. We just modify the same files more than once.
    for grdc in grdcs:
        year_range = range(grdc.year_begin, grdc.year_end + 1)
        with Path(f'{sim_path}/{grdc.run_dir}'):
            htessel_inputs = [HTESSELNameList(nml.read(f"run/{year}/input"))\
                              for year in year_range]
            mpr = MPRNameList(nml.read("mpr/mpr_global_parameter.nml"))
            for ht_input, year in zip(htessel_inputs, year_range):
                ht_input.read_only, mpr.read_only = False, False
                # modify_forcing_path(htessel, sim_path, run_id)
                modify_params(ht_input, mpr, dict(zip(x.name, [v for v in x])))
                special_treatments(ht_input)
                ht_input.read_only, mpr.read_only = True, True
                # write the changes
                ht_input.write(f"./run/{year}")
                mpr.write("./mpr")


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


def get_run_dirs(grdcs:list):
    return list({grdc.run_dir for grdc in grdcs})


class spot_setup_htcal(object):
    #
    def __init__(self,
                 control_file,
                 restart:bool,
                 clean_completed:bool,
                 nthreads:int,
                 basin_lookup='basin_lut.org'):
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
        blut = basin_lut(basin_lookup)
        #
        # We want to turn the training dictionary "inside-out". Consider the following example:
        #
        # training = {
        # '4145130': {'year_begin': 1979, 'year_end': 1981,
        #             'warmup': 120}, # single grdc
        # '5226800': {'year_begin': 1984, 'year_end': 1986,
        #             'warmup': 120}, # single grdc
        # '3269': {'grdc_ids' : [2589390], 'year_begin': 2000, 'year_end': 2001,
        #          'warmup': 120}, # basin with single station
        # }
        #
        # it creates three directories as follows:
        #
        # station_4145130
        # station_5226800
        # basin_3269
        #
        # Each contains a simulation with specified years. We need to run each simulation
        # once and at the same time access the specified station number (grdc_num) for
        # calculation of objective function. Each entry in `grdcs` list has this structure,
        # namely, grdc_id, run_directory, years and warmup. Iterating on this list we can
        # change the parameters of each simulation and calculate the objective function of
        # each grdc station. We also extract the run directories and store it in `self.run_dirs`
        # for ease of use, for example when running the simulations of mpr and htessel.
        #
        GRDC = namedtuple('GRDC',
                  ['grdc_id',
                   'run_dir',
                   'year_begin',
                   'year_end',
                   'warmup'])
        training = self.control_file.training
        self.grdcs = []
        for k in training.keys():
            basin_id, grdc_id = blut.get_ids(k)
            year_begin = training[k]['year_begin']
            year_end = training[k]['year_end']
            warmup = training[k]['warmup']
            #
            if grdc_id is None:
                assert basin_id == k
                assert len(training[k]['grdc_ids']) == 1,  'Multi-station is not supported'
                grdc_id = str(training[k]['grdc_ids'][0])
                run_dir = f'basin_{basin_id}'
            else:
                grdc_id = grdc_id
                run_dir = f'station_{grdc_id}'
            self.grdcs.append(
                GRDC(grdc_id,
                     run_dir,
                     year_begin,
                     year_end,
                     warmup))
        self.run_dirs = get_run_dirs(self.grdcs)
        # prepare
        self.create_run_directory(self.control_file_path)
        self.nthreads = nthreads
        self.rm_sim_folder = clean_completed

    def create_run_directory(self, root_path):
        if not self.restart:
            assert not os.path.isdir(f"{root_path}/runs"), f"runs directory exists."
            Path(f'{root_path}/runs').mkdir(exist_ok=True)

    def create_param_run_directory(self, root_path):
        # get all the simulation direcotories
        sim_folders = [f'{root_path}/runs/{x}' for x in get_dir(f'{root_path}/runs') if x.find('sim_') != -1]

        if sim_folders == []:
            sim_number = 1
        else:
            # get the last sim folder
            sim_number = max([int(re.findall(r".+sim_(\d+)", x)[0]) for x in sim_folders]) + 1

        Path(f'{root_path}/runs/sim_{sim_number}').mkdir()
        return f'{root_path}/runs/sim_{sim_number}'

        
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
        modify_basin_with_new_params(sim_path, self.grdcs, x)

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
            for grdc in self.grdcs:
                year_range = range(grdc.year_begin, grdc.year_end + 1)
                rivouts = []
                for year in year_range:
                    rivouts.append(
                        get_river_output(nc.Dataset(f"{sim_path}/{grdc.run_dir}/run/{year}/o_rivout_cmf.nc"),
                                         grdc.grdc_id)
                    )
                results[str(grdc.grdc_id)] = rivouts
            # concatenante the restuls before sending back
            # import pdb; pdb.set_trace()
            return {k: pd.concat(v).reset_index() for k, v in results.items()}


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
            #
            kges = {}
            for grdc in self.grdcs:
                grdc_id = grdc.grdc_id
                warmup = grdc.warmup
                obs, mod = get_discharge(evaluation[grdc_id], simulation[grdc_id])
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
            grdc.grdc_id : get_grdc_discharge(grdc.grdc_id) for grdc in self.grdcs
        }
