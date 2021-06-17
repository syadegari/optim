from pathlib import Path
import subprocess as sp
import os
import sys
import argparse

# some notes:
# starting a forward run for all baisin's:
# python3 prepare_run_lut.py -d '/work/kelbling/htcal_optim/fwrd_run' --basin --submit
# starting a forward run for all baisin's using the default MPR setup (NOT TESTED YET):
# python3 prepare_run_lut.py -d '/work/kelbling/htcal_optim/fwrd_run' -m default --basin --submit
# only prepare all basin dirs (be carful will spawn each preperation as a subshell):
# python3 prepare_run_lut.py -d '/work/kelbling/htcal_optim/fwrd_run' --basin
# only prepare all station dirs (be carful will spawn each preperation as a subshell):
# python3 prepare_run_lut.py -d '/work/kelbling/htcal_optim/fwrd_run'
# start dds calibrations with 1000 iteratinos for each station (NOT TESTED YET):
# python3 prepare_run_lut.py -d '/work/kelbling/htcal_optim/fwrd_run' -n 1000 --submit

# use custom basin or parameter lookuptables using the -l and -p argument

path_optim = (Path(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(path_optim))

import lutreader
import htcal_path

# all the global paths we need
htpath = htcal_path.get_paths()
gen_header = htcal_path.get_submitheader()

def write_control(basin, params, path, mpr_tf = 'zacharias'):
    cntrl = '''
# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = "{mpr_tf}"

training = {{
    '{basin_id}': {{'year_begin': {basin_syear}, 'year_end': {basin_eyear}, 'warmup': {basin_warmup}}}
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

def submit_job(run_id, run_dir, dirname_run, path_pythonenv, path_optim, n_dds, gen_header):
    if n_dds is None:
        runtime = '10:00:00'
        subname = 'fwrd.sub'
        runscript = '''
python3 ./prepare_domains.py -c {run_dir}/control_file
cd {run_dir}/default_sim/{dirname_run}
./run_mpr
./run_htessel
        '''.format(dirname_run    = dirname_run,
                   run_dir        = run_dir)
    else:
        runtime = '96:00:00'
        subname = 'optim.sub'
        runscript = '''
python3 ./prepare_domains.py -c {run_dir}/control_file
python3 ./driver.py -c {run_dir}/control_file.py -n {n_dds}
python3 ./plots.py -p {run_dir}
        '''.format(n_dds          = n_dds,
                   run_dir        = run_dir)

    submit = gen_header(time = runtime, run_path = run_dir,
                        mem = '15G', nnodes = '8', jobname = f'{run_id}_sopt_htcal')
    submit += '''
cd {path_optim}

source {path_pythonenv}
'''.format(runtime        = runtime,
           run_dir        = run_dir,
           run_id         = str(run_id),
           path_optim     = path_optim,
           path_pythonenv = path_pythonenv)
    submit += runscript
    open(os.path.join(run_dir, subname), 'w').write(submit)
    sub_path=os.path.join(run_dir, subname)
    sp.Popen(f"sbatch {sub_path}", shell=True).communicate()
    # print(submit)


parser = argparse.ArgumentParser()
parser.add_argument('-l', '--basin_lut', dest = 'basin_lut', default = 'basin_lut.org',
    help = "basin lut")
parser.add_argument('-p', '--param_lut', dest = 'param_lut', default = 'params.org',
    help = "param lut")
parser.add_argument('-m', '--mpr_tf', dest = 'mpr_tf', default = 'zacharias_res_1',
    help = "mpr transferfunction")
parser.add_argument('-n', '--ndds', dest = 'ndds', default = None,
    help = "Number of dds iterations if None no dds is run only one forward run")
parser.add_argument('--basin', action='store_true', help = "run on basins not station")
parser.add_argument('-d', '--run_dir', dest = 'run_dir',
    help = "run directory")
parser.add_argument('--submit', action='store_true',  help = "submit runs")
args = parser.parse_args()

lut = lutreader.basin_lut(args.basin_lut)
params = lutreader.param_lut(args.param_lut)

basins_done = []

for station_id in lut.lut.keys():
    if args.basin:
        if lut.lut[station_id]['basin'] not in basins_done:
            basin_id = lut.lut[station_id]['basin']
            basins_done.append(basin_id)
            path_basin = os.path.join(args.run_dir, 'basin_' + basin_id)
            print(f'Prepareing basin: {basin_id} in {path_basin}')
            os.makedirs(path_basin)
            write_control(lut.lut[station_id], params, path_basin, mpr_tf = args.mpr_tf)
            if args.submit:
                submit_job(basin_id, path_basin, 'basin_' + basin_id, htpath.path_pythonenv, path_optim, args.ndds, gen_header)
            else:
                sp.Popen(f'python3 prepare_domains.py -c {path_basin}/control_file.py', shell = True)
    else:
        path_basin = os.path.join(args.run_dir, 'station_' + station_id)
        print(f'Prepareing station: {station_id} in {path_basin}')
        os.makedirs(path_basin)
        write_control(lut.lut[station_id], params, path_basin, mpr_tf = args.mpr_tf)
        if args.submit:
            submit_job(station_id, path_basin, 'station_' + station_id, htpath.path_pythonenv, path_optim, args.ndds, gen_header)
        else:
            sp.Popen(f'python3 prepare_domains.py -c {path_basin}/control_file.py', shell = True)

