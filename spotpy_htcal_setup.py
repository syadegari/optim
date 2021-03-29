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
import glob
#
from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
import f90nml as nml
#
from pathlib import Path
from subprocess import Popen
from postproc import *
import multiprocessing as mp
from penalty import calculate_penalty_error


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


def create_basin_run_directory(path_root, path_sim, basins):
    """copies the default simulation into the sim folder"""
    for basin_nr in basins:
        shutil.copytree(f"{path_root}/default_sim/basin_{basin_nr}",
                        f"{path_sim}/basin_{basin_nr}", symlinks=True)


def modify_basin_with_new_params(sim_path, basins, control_file, x):
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
    for basin_nr in basins:
        # open the htessel in the sim_path
        # change to basin directory
        parent_dir = os.getcwd()
        os.chdir(f"{sim_path}/basin_{basin_nr}")
        # we open mpr and htessel files
        year_range = range(control_file.training[basin_nr]['year_begin'],
                           control_file.training[basin_nr]['year_end'] + 1)
        htessel_inputs = [HTESSELNameList(nml.read(f"run/{year}/input"))\
                          for year in year_range]
        mpr = MPRNameList(nml.read("mpr/mpr_global_parameter.nml"))
        for ht_input, year in zip(htessel_inputs, year_range):
            
            ht_input.read_only = False
            mpr.read_only = False
            # modify_forcing_path(htessel, sim_path, basin_nr)
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


def run_simulation(folder, num_threads=4):
    print(f'running {folder} with updated parameters ...')
    parent_folder = os.getcwd()
    os.chdir(folder)

    my_env = os.environ.copy()
    my_env['OMP_NUM_THREADS'] = str(num_threads)
    p = Popen('./run_programs', shell=True,
              stdout=open('output', 'w'),
              stderr=open('error', 'w'), env=my_env).communicate()

    p = Popen('./run_programs', shell=True,
              stdout=open('output', 'w'),
              stderr=open('error', 'w'), env=my_env).communicate()

    os.chdir(parent_folder)

        
class spot_setup_htcal(object):
    #
    def __init__(self, control_file):
        # import the control file
        control_file_path, control_file = ntpath.split(control_file)
        sys.path.insert(0, control_file_path)
        control_file = __import__(control_file)
        print(f"\nUsing control file: {control_file}\n")
        #
        self.control_file_path = control_file_path
        self.control_file = control_file 
        self.params = []
        for param_name, param_values in self.control_file.params.items():
            lower, upper, defulat = param_values
            self.params.append(spotpy.parameter.Uniform(param_name, lower, upper))

        self.basins = self.control_file.training.keys()
        # prepare
        self.create_run_directory(self.control_file_path)
        self.nProc = 4

    def create_run_directory(self, path):
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
        create_basin_run_directory(self.control_file_path, sim_path, self.basins)
        modify_basin_with_new_params(sim_path, self.basins, self.control_file, x)
        #
        #
        # run programs. Only run htessel if
        #                         1- No penalty exists in the control
        #                         2- When penalty exist, run when no penalty term is activated
        for basin_nr in self.basins:
            print(f'running mpr in basin_{basin_nr} in {sim_path} with updated parameters ...')
            parent_folder = os.getcwd()
            os.chdir(f"{sim_path}/basin_{basin_nr}")
            #
            p = Popen('./run_mpr', shell=True,
                      stdout=open('output_mpr', 'w'),
                      stderr=open('error_mpr', 'w')).communicate()
            os.chdir(parent_folder)
        #
        run_htessel = False
        try:
            penalty_errors = calculate_penalty_error(self.basins,
                                                     self.control_file.penalty,
                                                     sim_path)
            if np.array([v for _, v in penalty_errors.items()]).sum() != 0.0:
                print('mprin thresholds violated, skipping htessel run')
                print(penalty_errors)
                for basin_nr in self.basins:
                    shutil.rmtree(f'{sim_path}/basin_{basin_nr}/run')
                return penalty_errors
            else:
                run_htessel = True
        except AttributeError:
            print('no penalty formulation is found, running htessel')
            run_htessel = True
        if run_htessel:
            for basin_nr in self.basins:
                print(f'running htessel in basin_{basin_nr} in {sim_path} with updated parameters ...')
                parent_folder = os.getcwd()
                os.chdir(f"{sim_path}/basin_{basin_nr}")
                #
                my_env = os.environ.copy()
                my_env['OMP_NUM_THREADS'] = str(4)
                p = Popen('./run_htessel', shell=True,
                          stdout=open('output_htessel', 'w'),
                          stderr=open('error_htessel', 'w'), env=my_env).communicate()
                os.chdir(parent_folder)
        #
            results = {}
            for basin_nr in self.basins:
                year_range = range(self.control_file.training[basin_nr]['year_begin'],
                                   self.control_file.training[basin_nr]['year_end'] + 1)
                rivouts = []
                for year in year_range:
                    rivouts.append(get_river_output(nc.Dataset(f"{sim_path}/basin_{basin_nr}/run/{year}/o_rivout_cmf.nc"), basin_nr))
                results[basin_nr] = rivouts
            # concat the restuls before sending back
            return {
                basin_nr: pd.concat(results[basin_nr]).reset_index() for basin_nr in self.basins
            }
            

    def objectivefunction(self, simulation, evaluation):
        # get a key from the simulation
        k = list(simulation.keys())[0]
        if isinstance(simulation[k], float):
            with open(f"{self.control_file_path}/runs/res.txt", 'a') as res_file:
                res_file.write(f"{simulation}\n")
            #
            return sum(list(simulation.values()))
        else:
            sim_folders = [f'{self.control_file_path}/runs/{x}' \
                           for x in get_dir(f'{self.control_file_path}/runs') if x.find('sim_') != -1]
            sim_number = max([int(re.findall(r".+sim_(\d+)", x)[0]) for x in sim_folders])
            kges = {}
            for basin_nr in self.basins:
                obs, mod = get_discharge(evaluation[basin_nr], simulation[basin_nr])
                warmup = self.control_file.training[basin_nr]['warmup']
                # import pdb; pdb.set_trace()
                kges[basin_nr] = kge(obs[warmup : ], mod[warmup : ], components=True)
            # compute all the components of kge and write them into log but only return the kge itself
            kge_means = np.array(list(kges.values())).mean(axis=0)
            print(f"kge: {kge_means}")
            with open(f"{self.control_file_path}/runs/res.txt", 'a') as res_file:
                res_file.write(f"{kge_means}\n")
            return kge_means[0]


    def evaluation(self):
        return {
            basin_nr : get_grdc_discharge(basin_nr) for basin_nr in self.basins
        }

# setup = spot_setup_htcal("/p/home/jusers/yadegarivarnamkhasti1/juwels/project/build/optim/self.control_file.py")
