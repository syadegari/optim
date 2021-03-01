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
print(lut)

n_dds = 100

base_run_dir = '/work/kelbling/htcal_optim/single_basin_optim/test'

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

#SBATCH --time=08:00:00
#SBATCH --output=~/LOG.run.%j.out
#SBATCH --error=~/LOG.run.%j.err
#SBATCH --mem-per-cpu=16G
#SBATCH --export=ALL

cd {path_optim}

source {path_pythonenv}

python3 ./prepare_domains.py -c {path_basin}/control_file.py
python3 ./driver.py -c {path_basin}/control_file.py -n {n_dds}
'''.format(n_dds          = n_dds,
           path_basin     = path_basin,
           path_optim     = path_optim,
           path_pythonenv = path_pythonenv)
    open(os.path.join(path_basin, 'optim.sub'), 'w').write(submit)
    sub_path=os.path.join(path_basin, 'optim.sub')
    sp.Popen(f"sbatch {sub_path}", shell=True).communicate()
    # print(submit)

for _, basin in lut.lut.items():
    path_basin = os.path.join(base_run_dir, 'basin_' + basin['basin'])
    os.makedirs(path_basin)
    write_control(basin, params, path_basin)
    submit_job(basin['basin'], path_basin, htpath.path_pythonenv, path_optim, n_dds)



