import argparse
import os
import ntpath
import sys
from path import Path
from collections import namedtuple
import shutil
import subprocess as sp
import multiprocessing as mp

from htessel_namelist import HTESSELNameList
from cama_namelist import CamaNameList
from lutreader import basin_lut
import htcal_path
import f90nml as nml
import netCDF4 as nc

forcing_names = {
    'LWdown': 'CFORCLW',
    'PSurf':  'CFORCP',
    'Qair':   'CFORCQ',
    'Rainf':  'CFORCRAIN',
    'Snowf':  'CFORCSNOW',
    'SWdown': 'CFORCSW',
    'Tair':   'CFORCT',
    'Wind':   'CFORCU'}


def get_merge_output_name(forcing_name, year_begin, year_end):
    return f'{forcing_name}_{year_begin}_{year_end}.nc'


def get_info(control_file, blut) -> list:
    GRDC = namedtuple('GRDC',
                      ['grdc_id',
                       'run_dir',
                       'year_begin',
                       'year_end',
                       'warmup'])
    training = control_file.training
    grdcs = []
    for k in training.keys():
        basin_id, grdc_id = blut.get_ids(k)
        year_begin = training[k]['year_begin']
        year_end = training[k]['year_end']
        warmup = training[k]['warmup']
        #
        if grdc_id is None:
            assert basin_id == k
            assert len(training[k]['grdc_ids']) == 1,  'Multi-station is not supported'
            grdc_id = str(training[k]['grdc_ids'][0])
            run_dir = f'basin_{basin_id}'
        else:
            grdc_id = grdc_id
            run_dir = f'station_{grdc_id}'
        grdcs.append(
            GRDC(grdc_id,
                 run_dir,
                 year_begin,
                 year_end,
                 warmup))
    return grdcs


def htessel_run_cmd(year_begin, year_end):
    run_cmd = '''
echo "running squashed htessel between {year_begin} - {year_end}"
cd run/{year_begin}
#
./htessel >> ../../htessel.log  2>&1
#
tail -n100 log_CaMa.txt > log_CaMa_clipped.txt
rm log_CaMa.txt && mv log_CaMa_clipped.txt log_CaMa.txt
echo "htessel done"
cd ../..
'''
    res = htcal_path.runcommand(has_LAI_param=False)
    #
    return res.header_htessel + run_cmd.format(
        year_begin=year_begin,
        year_end=year_end
    )


def update_input_file(input_file, **kwargs):
    for k, v in kwargs.items():
        input_file[k] = v


def merge_forcing(merge_str):
    _, _ = sp.Popen(merge_str,
                shell=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE).communicate()


def htessel_params(n_time_steps:int, year_begin:int, year_end:int):
    return {
    # start or restart
        'LNF': True, # True = start, False   = restart
        #
        'IFYYYY': year_begin - 1, # reference year
        'IFMM': 12,               # reference month
        'IFDD': 31,               # reference day
        'IFTIM': 1800,            # reference time (hhmm)
        #
        'NINDAT': int(f'{year_begin}0101'), # run initial date in the form YYYYMMDD
        #
        'NSTART': 0,
        'NSTOP': n_time_steps - 1,
        #
        'NDFORC': n_time_steps,
    }


def cama_params(year_begin:int, year_end:int):
    #
    return {
        'LRESTART' : False,
        #
        'SDAYIN' : 1  ,
        'SHOURIN' : 0,
        'SMONIN' : 1,
        'SYEARIN' : year_begin,
        #
        'SDAY' : 1,
        'SHOUR' : 0,
        'SMON' : 1,
        'SYEAR' : year_begin,
        #
        'EDAY' : 1,
        'EHOUR' : 0,
        'EMON' : 1,
        'EYEAR' : year_end + 1
    }


def print_if(msg, flag:bool):
    if flag:
        print(msg)

def main():
    # argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--control-file', help="control file")
    parser.add_argument('-l', '--basin-lut', default='basin_lut.org', help="")
    parser.add_argument('-s', '--squashed-forcings', default='squashed_forcings', help="")
    parser.add_argument('-v', '--verbose', nargs='?', const=False, default=True)
    args = parser.parse_args()

    # retrieve path and sanity check
    verbose = args.verbose
    squashed_forcings = args.squashed_forcings
    control_file_path, _ = os.path.splitext(args.control_file)
    assert os.path.isfile(f"{control_file_path}.py"),\
    f"Control file {control_file_path}.py was not found"

    cf_path, cf_file = ntpath.split(control_file_path)

    #
    # insert the control file into path and initialize
    #
    sys.path.insert(0, cf_path)
    control_file = __import__(cf_file)
    cf = control_file

    path_root, _ = ntpath.split(cf.__file__)
    path_root_abs = os.path.abspath(path_root)

    grdcs = get_info(cf, basin_lut(args.basin_lut))
    run_dirs = {grdc.run_dir: (grdc.year_begin, grdc.year_end) for grdc in grdcs}

    print('Squashing the multiyear runs\n')
    print(f'Creating directory {squashed_forcings} in {path_root}')
    Path.mkdir(f'{path_root}/{squashed_forcings}')
    #
    #
    #

    # copy directories to work on them
    for run_dir, years_range in run_dirs.items():
        yb, ye = years_range

        print_if(f'\nCopy default_sim for {run_dir} to {squashed_forcings}\n', verbose)
        #
        # The followings are done here:
        #   1- Copy the default directory for each basin to squashed directory.
        #   2- For each basin, copy the forcing into the squashed directory.
        #   3- Merge the forcing into one forcing.
        #   4- After merging, remove all the files from squashed directory
        #      except the merged forcings.
        #
        sp.Popen(f'cp -r default_sim/{run_dir} {squashed_forcings}/{run_dir}',
                 shell=True,
                 cwd=path_root).communicate()
        # TODO: make a function from this part
        with Path(f'{path_root}/{squashed_forcings}/{run_dir}'):
            with Path('run'):
                for year in range(yb, ye + 1):
                    with Path(year):
                        ht_file = HTESSELNameList(nml.read('input'))
                        for forcing_name, forcing_kw in forcing_names.items():
                            print_if(f'copy forcing {forcing_name}: {ht_file[forcing_kw]}', verbose)
                            shutil.copy(ht_file[forcing_kw], '../..')
            #
            #
            #
            merge_cmd_list = []
            merged_names = []
            for forcing_name in forcing_names:
                #
                # we wanna produce strings like this
                # cdo -f nc4 -z zip_6 mergetime Tair_1984.nc Tair_1985.nc Tair_1986.nc Tair_1984_1986.nc
                #
                merge_inputs = ' '.join([f'{forcing_name}_{yr}.nc' for yr in range(yb, ye + 1)])
                merge_output = get_merge_output_name(forcing_name, yb, ye)
                merge_str = f'cdo -f nc4 -z zip_6 mergetime {merge_inputs} {merge_output}'
                merge_cmd_list.append(merge_str)
                merged_names.append(merge_output)
                print_if(f'Merge forcing {forcing_name} for yrs {yb} ... {ye}', verbose)
            #
            with mp.Pool(8) as pool:
                pool.map(
                    merge_forcing, merge_cmd_list
                )
            #
            #
            # remove everything except the merged files
            all_except_merged = [f for f in os.listdir() if f not in merged_names]
            for f in all_except_merged:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.remove(f)
                print_if(f'removing {f}', verbose)
        #
        # TODO: make a function from this part
        # In this part we go to default_sim folder and:
        #  1- Remove all the years under run directory for each basin
        #     except the first year. We use the first year to run the
        #     multi-year simulations
        #  2- In the first year directory, we update the path to all
        #     the forcings we merged and stored in squashed directory
        #  3- We update all the other information related to beginning
        #     and end of simulations in both htessel and cama input
        #     files. These are handeld in two subroutines `htessel_params`
        #     and `cama_params`.
        #  4- We update the `run_htessel` for multiyear run.
        #
        with Path(f'{path_root}/default_sim/{run_dir}/run'):
            # remove all yrs except the first year
            first_year = yb
            rest_years = range(yb + 1, ye + 1)
            for year in rest_years:
                print_if(f'removing year {year}', verbose)
                shutil.rmtree(str(year))
            with Path(str(first_year)):
                ht_file = HTESSELNameList(nml.read('input'))
                cama_file = CamaNameList(nml.read('input_cmf.nam'))
                ht_file.read_only, cama_file.read_only = False, False
                for forcing_name, forcing_kw in forcing_names.items():
                    merge_output = get_merge_output_name(forcing_name, yb, ye)
                    path_merged_output = f'{path_root_abs}/{squashed_forcings}/{run_dir}/{merge_output}'
                    ht_file[forcing_kw] = path_merged_output
                # do the rest of the modifications
                # get one of the merged forcings for number of time steps
                path_merged_output = ht_file[forcing_names['LWdown']]
                with nc.Dataset(path_merged_output) as nc_file:
                    n_time = nc_file.variables['time'].shape[0]
                update_input_file(ht_file,
                                  **htessel_params(n_time, yb, ye))
                update_input_file(cama_file,
                                  **cama_params(yb, ye))
                ht_file.read_only, cama_file.read_only = True, True
                ht_file.write()
                cama_file.write()
            with open('../run_htessel', 'w') as f:
                print_if('Replace HTESSEL run script', verbose)
                f.write(
                    htessel_run_cmd(year_begin=yb, year_end=ye)
                )


if __name__ == '__main__':
    main()
