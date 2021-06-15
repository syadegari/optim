import argparse
import sys
import os
import copy
from importlib import reload  
import numpy as np
import json

def parse_param_file(lines:list):
    '''parameters.dat is parsed and a dictionary parameter-name parameter-value is returned'''
    params = {}
    #
    for l in lines:
        k, v = l.split('=')
        k = k.lstrip().rstrip()
        params[k] = float(v)
        #
    return params


def parse_res(res:str): 
    '''each line of res.txt is parsed'''
    if res[0] == '[':
        return [float(x) for x in res[1:-2].split()]
    else:
        return eval(res)


def get_stats(result:list) -> list: 
    '''results for each optimization is given and as output the followings are produced:
          n_iter_penalty : number of iterations that the penalty part was active and htessel didn't run
          n_iter_optim   : number of iterations that htessel code has ran
          best_kge       : best KGE in the optimization
          best_sim_number: sim number where best KGE has been obtained
    '''
    n_iter_penalty = 0
    n_iter_optim = 0
    best_kge = -np.inf
    best_sim_number = 0
    for i_sim, res in enumerate(result, start=1):
        #
        if isinstance(res, list):
            n_iter_optim += 1
            if res[0] > best_kge:
                best_kge = res[0]
                best_sim_number = i_sim
                continue
        if isinstance(res, dict):
            n_iter_penalty += 1
    return n_iter_penalty, n_iter_optim, best_kge, best_sim_number

#                                                                                       #
# ------------------------------------------------------------------------------------- #
#                                                                                       #
parser = argparse.ArgumentParser()
parser.add_argument('-p', '--path',
                    help='path to the root of optimized simulations')
parser.add_argument('-n', '--num-stations', nargs='+', type=int,
                    help='station numbers separated by space')
parser.add_argument('-o', '--output-file', nargs='?', default='param_extract',
                    help='name of the output file containing extracted param information (.json)')
parser.add_argument('-v', '--verbose', nargs='?', const=True, default=False)
args = parser.parse_args()
#
path_root = args.path
num_stations = args.num_stations
verbose = args.verbose
output_name = args.output_file
#
path_output = f'{path_root}/{output_name}.json'
if os.path.exists(path_output):
    raise FileExistsError(f'''
    File {output_name}.json already exists in {path_root}. 
    Use a different output name or rename/move the original file''')
#

results = {}
original_path = copy.deepcopy(sys.path)

for idx, num_station in enumerate(num_stations):
    # get the control file
    control_file_path = f'{path_root}/station_{num_station}'
    sys.path = copy.deepcopy(original_path)
    sys.path.insert(0, control_file_path)
    #
    if idx > 0:
        control_file = reload(control_file)
    else:
        control_file = __import__('control_file')
    if verbose:
        print('using the control file at: ', control_file.__file__)
    training = control_file.training
    #
    year_begin = training[str(num_station)]['year_begin']
    year_end = training[str(num_station)]['year_end']
    warmup = training[str(num_station)]['warmup']
    mpr_tf = control_file.mpr_tf

    res_file = open(f'{path_root}/station_{num_station}/runs/res.txt').readlines()

    optim_results = []
    for i_line in range(1, len(res_file) // 2, 2):
        optim_results.append(parse_res(res_file[i_line]))
    
    _, _, best_kge, best_sim_num = get_stats(optim_results)
    param_lines = open(f'{path_root}/station_{num_station}/runs/sim_{best_sim_num}/parameters.dat').readlines()
    param_dict = parse_param_file(param_lines)

    results[num_station] = {
        'year_begin': year_begin,
        'year_end': year_end,
        'warmup': warmup,
        'params': param_dict,
        'best_sim_number': best_sim_num,
        'best_kge': best_kge,
        'mpr_tf': mpr_tf
    }

    if verbose:
        print(
            f'''
            Adding parameters for station_{num_station}:
                best_kge = {best_kge:.3f}
                sim folder of these results is in {path_root}/station_{num_station}/runs/sim_{best_sim_num}
            '''
        )

if verbose:
    print('Writing the extracted parameter information to:')
    print('  ', path_output)
open(path_output, 'w').write(json.dumps(results, indent=4))
