import sys
sys.path.insert(0, "/work-local/yadegari/optim_Eve/spotpy")
# sys.path.insert(0, "/Users/yadegari/Documents/code/optim/spotpy")
import spotpy
#
import numpy as np
import pandas as pd
import netCDF4 as nc
# import matplotlib.pyplot as plt
#
import ntpath
import sys
import os
import os.path
import re
import shutil
#
sys.path.insert(0, "/work-local/yadegari/optim_Eve/aux/")
# sys.path.insert(0, "/Users/yadegari/Documents/code/optim/aux")
from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
import f90nml as nml
#
from pathlib import Path
from subprocess import Popen
from postproc import *


def get_dir(path):
    return [x for x in os.listdir(path) if os.path.isdir(f'{path}/{x}')]

# path -+
#       |-> run/ [sim_1, sim_2, ...] +
#                                    |-> [basin_1, basin_2, ...]
# path/run/sim_13/basin_4999



   




def write_params_file(sim_path, x):
    fh = open(f'{sim_path}/parameters.dat', 'w')
    for param_name, param_val in zip(x.name, [val for val in x]):
        fh.write(f"{param_name} = {param_val}\n")
    fh.close()


def create_basin_run_directory(path, basin_names):
    """copies the default simulation into the sim folder"""
    for basin_name in basin_names:
        _, name = ntpath.split(basin_name)
        # currently we are in aux folder, should go up one folder to get the control file path
        shutil.copytree(f"../{name}", f"{path}/{basin_name}")


def modify_basin_with_new_params(sim_path, basins, x):
    for basin_name in basins:
        # open the htessel in the sim_path
        _, name = ntpath.split(basin_name)
        # change to basin directory
        parent_dir = os.getcwd()
        os.chdir(f"{sim_path}/{name}/")
        #
        htessel = HTESSELNameList(nml.read("input"))
        mpr = MPRNameList(nml.read("mpr_global_parameter.nml"))
        htessel.read_only = False
        mpr.read_only = False
        # modify_forcing_path(htessel, sim_path, basin_name)
        modify_params(htessel, mpr, dict(zip(x.name, [v for v in x])))
        special_treatments(htessel)
        htessel.read_only = True
        mpr.read_only = True
        # write the changes
        htessel.nml.write(htessel.tag, force=True)
        mpr.nml.write(mpr.tag, force=True)
        # change to parent directory
        os.chdir(parent_dir)


def modify_params(htessel, mpr, params_dict):
    for k, v in params_dict.items():
        if k in htessel.get_all_model_parameters():
            htessel[k] = v
        elif k in mpr.get_all_model_parameters():
            mpr[k] = v
        else:
            raise Exception 


def special_treatments(nmlist):
    if nmlist.tag == 'input':
        nmlist['rez0ice'] = int(nmlist['rez0ice'])
    return nmlist


def run_simulation(folder, num_threads=8):
    parent_folder = os.getcwd()
    os.chdir(folder)

    my_env = os.environ.copy()
    my_env['OMP_NUM_THREADS'] = str(num_threads)
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
        print()
        print(f"Using control file: {control_file}")
        print()
        #
        self.control_file_path = control_file_path
        self.control_file = control_file 
        self.warmup = control_file.warmup_day
        self.params = []
        for param_name, param_values in self.control_file.params.items():
            lower, upper, defulat = param_values
            self.params.append(spotpy.parameter.Uniform(param_name, lower, upper))

        self.basins = self.control_file.training.keys()
        # prepare
        self.create_run_directory(self.control_file_path)
      

    def create_run_directory(self, path):
        assert not os.path.isdir(f"{path}/runs"), f"runs directory exists."        
        Path(f'{path}/runs').mkdir(exist_ok=True)


    def create_param_run_directory(self, path):
        # get all the simulation direcotories
        sim_folders = [f'{path}/runs/{x}' for x in get_dir(f'{path}/{runs}') if x.find('sim_') != -1]    

        if sim_folders == []:
            sim_number = 1
        else:
            # get the last sim folder
            sim_number = max([int(re.findall(r".+sim_(\d+)", x)[0]) for x in sim_folders]) + 1

        Path(f'{path}/{runs}/sim_{sim_number}').mkdir()
        return f'{path}/{runs}/sim_{sim_number}'

        
    def parameters(self):
        return spotpy.parameter.generate(self.params)


    def simulation(self, x):
        # TODO: replace this after fixing the csv-file problem
        with open(f"../{runs}/res.txt", 'a') as res_file:
            print("parameters: ", [_ for _ in x], file=res_file)
        print("parameters: ", [_ for _ in x])
        #
        sim_path = self.create_param_run_directory(self.control_file_path)
        write_params_file(sim_path, x)
        create_basin_run_directory(sim_path, self.basins)
        modify_basin_with_new_params(sim_path, self.basins, x)

        for basin in self.basins:
            _, basin_folder = ntpath.split(basin)
            run_simulation(f"{sim_path}/{basin_folder}", num_threads=4)
        return {
            k : get_river_output(nc.Dataset(f"{sim_folder}/o_rivout_cmf.nc"), k) for k in self.basins
        }


    def objectivefunction(self, simulations, evaluations):
        for basin in self.basins:
            obs, mod = get_discharge(evaluations[basin], simulations[basin])
            kge(obs[self.warmup : ], mod[self.warmup : ])



    # def simulation(self, x):
    #     # TODO: replace this after fixing the csv-file problem
    #     with open(f"../{runs}/res.txt", 'a') as res_file:
    #         print("parameters: ", [_ for _ in x], file=res_file)
    #     print("parameters: ", [_ for _ in x])
    #     #
    #     sim_path = self.create_param_run_directory(self.control_file_path)
    #     write_params_file(sim_path, x)
    #     create_basin_run_directory(sim_path, self.basins)
    #     modify_basin_with_new_params(sim_path, self.basins, x)
    #     for basin in self.basins:
    #         # run the basins
    #         _, basin_folder = ntpath.split(basin)
    #         run_simulation(f"{sim_path}/{basin_folder}", num_threads=4)
            
        
            


    def evaluation(self):
        return {
            k : get_grdc_discharge(k) for k in self.basins
        }


        

# setup = spot_setup_htcal("/p/home/jusers/yadegarivarnamkhasti1/juwels/project/build/optim/self.control_file.py")

