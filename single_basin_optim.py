import lutreader
import subprocess as sp
import os

lut = lutreader.basin_lut('basin_lut.org')
params = lutreader.param_lut('params.org')
print(lut)

n_dds = 100

base_dir = './'
path_optim = ''
path_pythonenv = ''
path_control = ''

mpr_tf = 'zacharias'

def write_control(basin, params, path, mpr_tf = 'zacharias'):
    cntrl = '''
# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = {mpr_tf}

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
    # open(os.path.join(path, 'control_file.py'), 'w').write(run_programs)
    print(cntrl)

def submit_job(basin, path_optim, path_pythonenv, path_control, n_dds):
    submit = '''
#!/usr/bin/bash

#SBATCH --time=08:00:00
#SBATCH --output=~/LOG.run.%j.out
#SBATCH --error=~/LOG.run.%j.err
#SBATCH --mem-per-cpu=16G
#SBATCH --export=ALL

cd {path_optim}

source {path_pythonenv}

python3 ./prepare_domains.py -c {path_control}
python3 ./driver.py -c /test_run/control_file.py -n {n_dds}
'''.format(n_dds          = n_dds,
           path_optim     = path_optim,
           path_pythonenv = path_pythonenv,
           path_control   = path_control)
    # open(os.path.join(path, 'optim.sub'), 'w').write(submit)
    # sp.Popen("sbatch optim.sub", shell=True).communicate()
    print(submit)

for _, basin in lut.lut.items():
    # os.makedirs(base_dir)
    write_control(basin, params, base_dir)
    submit_job(basin['basin'], path_optim, path_pythonenv, path_control, n_dds)



