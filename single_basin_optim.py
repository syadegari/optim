from pathlib import Path
import subprocess as sp
import os
import sys

path_optim = (Path(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(path_optim))

import lutreader
import htcal_path

# all the global paths we need
htpath = htcal_path.get_paths()

lut = lutreader.basin_lut('basin_lut.org')
params = lutreader.param_lut('params.org')

n_dds = 1000

base_run_dir = '/work/kelbling/htcal_optim/single_basin_optim/only_mpr'

# run multple optimizations with different default parameters
jitter = None
# jitter = [-2, -1, 1, 2]

# run multiple oprimizations with the min and max values of each iteration being moved towards the default value
# decrease = None
decrease = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]



mpr_tf = 'zacharias'

def write_control(basin, params, path, mpr_tf = 'zacharias'):
    cntrl = '''
# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = "{mpr_tf}"

training = {{
    {basin_id}: {{'year_begin': {basin_syear}, 'year_end': {basin_eyear}, 'warmup': {basin_warmup}}}
}}

validation = {{}}

forcing_files = 'single'

#                    lower             upper             default
params = {{
'''.format(mpr_tf       = mpr_tf,
           basin_id     = basin['basin'],
           basin_syear  = basin['optim_syear'],
           basin_eyear  = basin['optim_eyear'],
           basin_warmup = basin['warmupdays'])
    for _, pp in params.lut.items():
        if pp['flag_optimize']:
            cntrl += '         "{p_name}" : [{p_lower}, {p_upper}, {p_default}],\n'.format(
                p_name    = pp['parameter'],
                p_upper   = pp['min'],
                p_lower   = pp['max'],
                p_default = pp['default']
            )
    cntrl += ' }'
    open(os.path.join(path, 'control_file.py'), 'w').write(cntrl)
    # print(cntrl)

def submit_job(basin, path_basin, path_pythonenv, path_optim, n_dds):
    submit = '''#!/usr/bin/bash

#SBATCH --time=80:00:00
#SBATCH --output={path_basin}/LOG.run.%j.out
#SBATCH --error={path_basin}/LOG.run.%j.err
#SBATCH --mem-per-cpu=16G
#SBATCH --export=ALL
#SBATCH --job-name={basin}_sopt_htcal

cd {path_optim}

source {path_pythonenv}

python3 ./prepare_domains.py -c {path_basin}/control_file.py
python3 ./driver.py -c {path_basin}/control_file.py -n {n_dds}
python3 ./plots.py -p {path_basin}
'''.format(n_dds          = n_dds,
           path_basin     = path_basin,
           basin          = str(basin),
           path_optim     = path_optim,
           path_pythonenv = path_pythonenv)
    open(os.path.join(path_basin, 'optim.sub'), 'w').write(submit)
    sub_path=os.path.join(path_basin, 'optim.sub')
    sp.Popen(f"sbatch {sub_path}", shell=True).communicate()
    # print(submit)

if jitter is None and decrease is None:
    for _, basin in lut.lut.items():
        path_basin = os.path.join(base_run_dir, 'basin_' + basin['basin'])
        os.makedirs(path_basin)
        write_control(basin, params, path_basin)
        submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)
elif jitter is not None and decrease is None:
    # print('#################################')
    # print('#################################')
    # print('#################################')
    # print( 'Starting optimization for:')
    # params.print_lut()
    for _, basin in lut.lut.items():
        path_basin = os.path.join(base_run_dir, 'default', 'basin_' + basin['basin'])
        os.makedirs(path_basin)
        write_control(basin, params, path_basin)
        submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)
    for jit in jitter:
        params.jitter_lut(jit)
        # print('#################################')
        # print('#################################')
        # print('#################################')
        # print( 'Starting optimization for:')
        # params.print_lut()
        for _, basin in lut.lut.items():
            path_basin = os.path.join(base_run_dir, f'jit_{jit}', 'basin_' + basin['basin'])
            os.makedirs(path_basin)
            write_control(basin, params, path_basin)
            submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)
        params.reset_lut()
elif jitter is None and decrease is not None:
    # print('#################################')
    # print('#################################')
    # print('#################################')
    # print( 'Starting optimization for:')
    # params.print_lut()
    for _, basin in lut.lut.items():
        path_basin = os.path.join(base_run_dir, 'default', 'basin_' + basin['basin'])
        os.makedirs(path_basin)
        write_control(basin, params, path_basin)
        submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)
    for ii in decrease:
        params.decrease_interval(ii)
        # print('#################################')
        # print('#################################')
        # print('#################################')
        # print( 'Starting optimization for:')
        # params.print_lut()
        for _, basin in lut.lut.items():
            path_basin = os.path.join(base_run_dir, f'decrease_{ii}', 'basin_' + basin['basin'])
            os.makedirs(path_basin)
            write_control(basin, params, path_basin)
            submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)
        params.reset_lut()


