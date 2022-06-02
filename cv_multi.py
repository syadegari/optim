import argparse
import os
import sys
from path import Path
import ntpath
import json
import re
from typing import Tuple
import mpi4py.futures as futures
from itertools import repeat
import subprocess as sp
import copy
import pprint
import numpy as np
import pathlib

from squash_multiyear import get_info
from lutreader import basin_lut
from modify_sim import modify_sim_param
from util import import_control_file, get_station_number, get_optim_path

DEBUG = True

def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-c', '--control-file', help="control file")
    parser.add_argument('--cv-folder-path', help="Location of CV folder")
    parser.add_argument('--cv-stations',
                        help="json file with cv stations information"
                        )
    parser.add_argument('-l', '--basin-lut',
                        default='basin_lut.org',
                        help="Path to (including the fliename) 'basin_lut.org'"
                        )
    parser.add_argument('--warmup',
                        default=365,
                        type=int,
                        help="Warmup days used in postprocessing. Written to control file."
                        )
    parser.add_argument('--squash-sim',
                    nargs='?', const=True, default=False,
                    help='Disables water balance check'
                    )
    parser.add_argument('--disable-wbcheck',
                    nargs='?', const=True, default=False,
                    help='Disables water balance check.\n \
                        Only works when --squash-sim is enabled'
                    )
    parser.add_argument('--htessel-exec',
                    nargs='?', const="", default="default",
                    help='Replaces with an executable other than the default.\n \
                    Executable should be available in exec folder.\n \
                    With "default" uses the executable that is defined in htcal_path.\n \
                        Only works when --squash-sim is enabled'
                    )
    parser.add_argument('--calculate-kge',
                    nargs='?', const=True, default=False,
                    help='Calculates kge'
                    )
    return parser.parse_args()    


def run_shell_cmd(cmd, cwd):
    out, err = sp.Popen(cmd,
                        shell=True,
                        cwd=cwd,
                        stdout=sp.PIPE,
                        stderr=sp.PIPE).communicate()
    return out, err


def create_control_file(cv_info, control_file_path):
    st_num = get_station_number(cv_info['station'])
    
    training = \
    {
        st_num:
            {
                'year_begin': cv_info['year_begin'],
                'year_end': cv_info['year_end'],
                'warmup': cv_info['warmup']
            }
    }

    cf, _, _ = import_control_file(control_file_path)
    names = [name for name in dir(cf) if not name.startswith('__')]
    with open('control.py', 'w') as f:
        pp = pprint.PrettyPrinter(indent=4, stream=f)
        # first print training
        print('training= \\', file=f)
        pp.pprint(training)
        print('', file=f)
        # iterate on the rest
        for name in list(set(names) - {'training'}):
            print(f'{name} = \\', file=f)
            pp.pprint(getattr(cf, name))
            print('', file=f)


def create_default_sim(cv_info:dict, 
                       control_file_path:str):
    '''
    TODO: draw tree output for documentation here
    '''
    # we should be in CV/station_123456
    create_control_file(cv_info, control_file_path)
        
    cmd = ' '.join(
        [
            'python',
            f'{get_optim_path()}/prepare_domains.py',
            '-c control.py',
            f'-l {get_optim_path()}/basin_lut.org'
        ]
    )
    cwd = '.'
    _, _ = run_shell_cmd(cmd, cwd)


def modify_params(station, param_set):
    with Path(f'default_sim/{station}'):
        modify_sim_param(param_set)


def calculate_and_write_kge():
    ...


def gather_kge():
    ...


def run_squash(disable_wb_check,
               htessel_exec):
    cmd = ' '.join(
        [
            'python',
            f'{get_optim_path()}/squash_multiyear.py',
            '-c control.py',
            f'-l {get_optim_path()}/basin_lut.org',
            '-q',
            (lambda: '--disable-wbcheck' if disable_wb_check else '')(),
            f'--htessel-exec {htessel_exec}'
        ]
    )
    cwd = '.'
    _, _ = run_shell_cmd(cmd, cwd)


def run_mpr(name):
    cmd = './run_mpr'
    cwd = f'default_sim/{name}'
    _, _ = run_shell_cmd(cmd, cwd)


def run_htessel(name):
    cmd = './run_htessel'
    cwd = f'default_sim/{name}'
    _, _ = run_shell_cmd(cmd, cwd)


def worker_fn(cv_info:dict,
              cf_address: str,
              param_set:dict,
              squash_sim:bool,
              disable_wb_check:bool,
              htessel_exec:str,
              calculate_kge:bool) -> None:
    '''
    cv_info: information we need to construct cross validation station
             e.g.: {'station': 'station_123456',
                    'year_begin': 1988,
                    'year_end': 1992,
                    'warmup': 365}
    cf_address: address of the control_file we used for optimization.
                we use this file together with cv_info to construct
                a new control file for the station in validation set. 
                (include filename and extension)
    param_set: best param set from optimization
    '''
    with Path(cv_info['station']).mkdir():
        if DEBUG: print(f'in worker: {cv_info}')
        create_default_sim(cv_info, cf_address)
        modify_params(cv_info['station'], param_set)
        if squash_sim:
            run_squash(disable_wb_check, htessel_exec)
        run_mpr(cv_info['station'])
        run_htessel(cv_info['station'])
        if calculate_kge:
            calculate_and_write_kge()


def parse_params(param_str:str, cf_params:dict) -> dict:
    param_list = re.match('^parameters:  \[(.+)]', param_str)[1].split(',')
    params_float = [float(p) for p in param_list]
    return dict(zip(cf_params.keys(), params_float,))


def get_best_param_set(res_file_lines:list, cf_params:dict) -> Tuple[float, int, dict]:
    '''Assumes the param dictionary has the same order as params'''
    max_kge = -np.inf
    best_param_set = {}
    best_iter_num = -1
    lines = res_file_lines
    for idx, (params, vals) in enumerate(zip(lines[::2], lines[1::2]), start=1):
        if vals[0] == '[':
            kge = float(re.match('\[(.+)\]', vals)[1].split()[0])
            if max_kge < kge:
                max_kge = kge
                best_param_set = parse_params(params, cf_params)
                best_iter_num = idx
    #
    return max_kge, best_iter_num, best_param_set


def create_cv_folder(cv_folder_path:str) -> None:
    # use the folder if it exists
    if not os.path.exists(f'{args.cv_folder_path}/CV/'):
        os.makedirs(f'{args.cv_folder_path}/CV/',)
    # path_root_abs = os.path.abspath(path_root)


def write_best_param_set(path_root:str,
                          cv_folder_path:str,
                          optim_params:dict) -> None:
    # read res.txt
    with open(f'{path_root}/runs/res.txt') as f:
        lines = f.readlines()
    #
    max_kge, best_iter_num, best_param_set = get_best_param_set(lines, optim_params)
    #
    with open(f'{cv_folder_path}/CV/best_param_set.json', 'w') as f:
        json.dump(
            {
                'simulation': path_root,
                'iteration': best_iter_num,
                'max_kge': max_kge,
                'best_param_set': best_param_set
            },
            f,
            indent=4
        )


def main():

    args = parse_arguments()

    cf, path_root, cf_name = import_control_file(args.control_file)

    create_cv_folder(args.cv_folder_path)

    grdcs = get_info(cf, basin_lut(args.basin_lut))
    run_dirs = {grdc.run_dir: (grdc.year_begin, grdc.year_end) for grdc in grdcs}

    #
    with open(args.cv_stations, 'r') as f:
        cvs = json.load(f)
    # we use these for CV
    cv_ = list(set(cvs) - set(run_dirs))
    cv_ = [
        {'station': st,
         'year_begin': cvs[st]['yb'][0],
         'year_end': cvs[st]['yb'][0] + cvs[st]['nyrs'][0] - 1,
         'warmup': args.warmup
        } for st in cv_
    ]
    #
    write_best_param_set(path_root,
                         args.cv_folder_path,
                         cf.params)
    #
    path_worker = copy.deepcopy(sys.path)
    path_worker.insert(0, get_optim_path())
    #
    with Path(f'{args.cv_folder_path}/CV'):
        with futures.MPIPoolExecutor(path=path_worker) as pool:
            pool.starmap(
                worker_fn,
                zip(cv_,
                    repeat(f'{path_root}/{cf_name}.py', len(cv_)),
                    repeat(best_param_set, len(cv_)),
                    repeat(args.squash_sim, len(cv_)),
                    repeat(args.disable_wbcheck, len(cv_)),
                    repeat(args.htessel_exec, len(cv_)),
                    repeat(args.calculate_kge, len(cv_))
                    )
            )
    #
    if args.calculate_kge:
        gather_kge()


if __name__ == '__main__':
    main()
