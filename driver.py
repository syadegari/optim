#!/usr/bin/env python

import argparse
import re
import os.path
import shutil
import pathlib
import sys
sys.path.insert(0, f'{pathlib.Path(__file__).parent.resolve()}/spotpy/')
from spotpy.algorithms import dds
sys.path.insert(0, f'{pathlib.Path(__file__).parent.resolve()}/')
from spotpy_htcal_setup import spot_setup_htcal
import numpy as np




if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--control-file',
                        help="control file, including the path")
    parser.add_argument('-n', '--num-sample',
                        type=int, help="number of samples")
    parser.add_argument('-l', '--basin_lut',
                        dest = 'basin_lut', default = 'basin_lut.org',
                        help = "basin lut")
    parser.add_argument('-r', '--restart', dest='restart',
                        action='store_true', default=False,
                        help='restart from the last completed simulation')
    parser.add_argument('--clean-completed', dest='clean_completed',
                        action='store_true', default=False,
                        help='clean each completed simulation or not')
    parser.add_argument('--nthreads', dest='nthreads', nargs='?',
                        default=4, type=int,
                        help='[DEPRECATED] default number of threads for htessel')
    args = parser.parse_args()

    control_file_path, _ = os.path.splitext(args.control_file)
    assert os.path.isfile(f"{control_file_path}.py"),\
        f"Control file {control_file_path}.py was not found"
    assert os.path.isfile(f"{args.basin_lut}"),\
        f"Control file {args.basin_lut} was not found"

    if args.restart:
        print('\nRestart option is enabled:')
        # runs_path
        path_runs_dir, _ = os.path.split(control_file_path)
        path_res_file = path_runs_dir + '/runs/res.txt'
        res_lines = open(path_res_file).readlines()
        if len(res_lines) % 2 == 1:
            print('last parameter set is without results')
            incomplete_sim = f'sim_{len(res_lines) // 2 + 1}'
            print(f'removing {incomplete_sim}')
            shutil.rmtree(f'{path_runs_dir}/runs/{incomplete_sim}')
            res_lines.pop()
            open(path_res_file, 'w').writelines(res_lines)
        #
        print(f'Currently {len(res_lines) // 2} iterations have been performed')
        print('Obtaining the best parameter set for restart ...')
        max_kge = -np.inf
        max_params_str = ''
        max_param_sim_num = 0
        total_iter_so_far = len(res_lines) // 2
        #
        for sim_num, (params, res) in enumerate(zip(res_lines[::2], res_lines[1::2]), start=1):
            if res[0] == '[':
                kges = [float(x) for x in res[1:-2].split()]
                if max_kge < kges[0]:
                    max_kge = kges[0]
                    max_params_str = params
                    max_param_sim_num = sim_num
        max_params = [float(x) for x in re.match(r'.+\[(.+)\]', max_params_str)[1].split(',')]
        print(f'  found parameter set for restart at sim_{max_param_sim_num}')
        print(f'  with max kge obtained so far: {max_kge}')
        print(f'  with the following parameter set that is going to be used as an initial point for restart')
        print(f'  {max_params}\n')
    # debug info
    import sys
    print(sys.argv)
    #
    spot_setup = spot_setup_htcal(control_file_path,
                                  args.restart,
                                  args.clean_completed,
                                  args.nthreads,
                                  args.basin_lut)

    sampler = dds(spot_setup, dbname="htcal", save_sim=False)

    if not args.restart:
        sampler.sample(int(args.num_sample))
    else:
        sampler.sample(int(args.num_sample),
                      x_initial=max_params, init_iter_num=total_iter_so_far)
