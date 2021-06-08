import argparse
import json
import os
import subprocess as sp
import f90nml as nml
from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
from spotpy_htcal_setup import modify_params, special_treatments

control_file = '''
mpr_tf = \'{mpr_tf}\'

# year_end is inclusive
training = {{
   \'{station_number}\': {{'year_begin': {year_begin}, 'year_end': {year_end}, 'warmup': {warmup}}},
}}
'''

#                                                                                       #
# ------------------------------------------------------------------------------------- #
#                                                                                       #
parser = argparse.ArgumentParser()
parser.add_argument('-p', '--param-file')
parser.add_argument('-o', '--output-folder', nargs='?', default='cross_validation')
parser.add_argument('-v', '--verbose', nargs='?', const=True, default=False)
args = parser.parse_args()

#
param_file = args.param_file
path_root, _ = os.path.split(param_file)

output_folder = args.output_folder
verbose = args.verbose

sims_specs = json.load(open(f'{param_file}'))

station_nums = list(sims_specs)

os.mkdir(f'{path_root}/{output_folder}')
for num_station in station_nums:
    stations = list(set(station_nums) - set([num_station]))
    os.mkdir(f'{path_root}/{output_folder}/station_{num_station}')
    # here we write the parameters' file that all the sub-simulations under it will inherit
    # for book keeping and debug/checks
    params = sims_specs[num_station]['params']
    open(f'{path_root}/{output_folder}/station_{num_station}/parameters.json',
         'w').write(json.dumps(params, indent=4))
    #
    for num in stations:
        # create run folders
        os.mkdir(f'{path_root}/{output_folder}/station_{num_station}/station_{num}')
        mpr_tf = sims_specs[num]['mpr_tf']
        year_begin = sims_specs[num]['year_begin']
        year_end = sims_specs[num]['year_end']
        warmup = sims_specs[num]['warmup']
        control_file_path = f'{path_root}/{output_folder}/station_{num_station}/station_{num}/control_file.py'
        with open(control_file_path, 'w') as control_file_handle:
            control_file_handle.write(control_file.format(
            mpr_tf=mpr_tf,
            station_number=num,
            year_begin=year_begin,
            year_end=year_end,
            warmup=warmup
        ))
        #
        # we run everything here with parameters of the parent
        #
        # first create default sim by calling prepare_basin
        cmd = f'python prepare_domains.py -c {control_file_path}'
        out, err = sp.Popen(cmd, shell=True, stderr=sp.PIPE, stdout=sp.PIPE).communicate()
        if err:
            print('Error detected')
            print(err)
        print(out.decode('utf-8'))
        # now we update mpr and htessel inputs with params dict
        year_range = range(year_begin, year_end + 1)
        sim_folder = f'{path_root}/{output_folder}/station_{num_station}/station_{num}/default_sim/station_{num}'
        htessel_parent = f'{sim_folder}/run'
        mpr_folder = f'{sim_folder}/mpr'
        htessel_inputs = [HTESSELNameList(nml.read(f"{htessel_parent}/{year}/input"))\
                          for year in year_range]
        mpr = MPRNameList(nml.read(f"{mpr_folder}/mpr_global_parameter.nml"))
        #
        for ht_input, year in zip(htessel_inputs, year_range):
            #
            ht_input.read_only = False
            mpr.read_only = False
            # 
            modify_params(ht_input, mpr, params)
            special_treatments(ht_input)
            ht_input.read_only = True
            mpr.read_only = True
            # write the changes
            ht_input.write(f"{htessel_parent}/{year}")
            mpr.write(f"{mpr_folder}")