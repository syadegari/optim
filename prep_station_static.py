from pathlib import Path
import subprocess as sp
import os
import sys
import argparse


path_optim = (Path(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(str(path_optim))

import lutreader
import htcal_path

# all the global paths we need
htpath = htcal_path.get_paths()
gen_header = htcal_path.get_submitheader()

def submit_job(run_dir, station_id, basin_id, mpr_dir, static_dir, gen_header):
    station_work_dir = os.path.join(run_dir, 'station_' + station_id)
    mpr_in_data_dir = os.path.join(mpr_dir, 'basin_' + basin_id)
    mpr_data_dir = os.path.join(mpr_dir, 'station_' + station_id)
    static_data_dir = os.path.join(static_dir, 'station_' + station_id)
    os.makedirs(station_work_dir)
    submit = gen_header(time = '1:00:00', run_path = station_work_dir,
                        mem = '15G', nnodes = '8', jobname = f'{station_id}_gen_mprin')
    submit = '''

mkdir -p {mpr_data_dir}

module load foss/2019b
module load CDO


cd {station_work_dir}

cdo selname,Mask {static_data_dir}/surfclim l1mask.nc
cdo griddes {mpr_in_data_dir}/SNDPPT_M.nc | sed -e 's/generic/lonlat/' > griddes

cdo -P 8 remapdis,griddes l1mask.nc l0mask.nc

cdo setmissval,255 l0mask.nc cs_l0mask.nc
cdo setmissval,-32768 l0mask.nc blk_l0mask.nc

cdo ifthen cs_l0mask.nc {mpr_in_data_dir}/CLYPPT_M.nc {mpr_data_dir}/CLYPPT_M.nc
cdo ifthen cs_l0mask.nc {mpr_in_data_dir}/SNDPPT_M.nc {mpr_data_dir}/SNDPPT_M.nc
cdo ifthen blk_l0mask.nc {mpr_in_data_dir}/BLDFIE_M.nc {mpr_data_dir}/BLDFIE_M.nc
cdo ifthen l1mask.nc {static_data_dir}/surfclim {mpr_data_dir}/surfclim

'''.format(station_work_dir = station_work_dir,
           station_id       = str(station_id),
           basin_id         = basin_id,
           mpr_data_dir     = mpr_data_dir,
           mpr_in_data_dir  = mpr_in_data_dir,
           static_data_dir  = static_data_dir)
    sub_path=os.path.join(station_work_dir, 'submit.sh')
    open(sub_path, 'w').write(submit)
    sp.Popen(f"sbatch {sub_path}", shell=True).communicate()
    # print(submit)


static_dir = '/data/htcal/data/processed/static/15min/ini_data'
mpr_dir = '/data/htcal/data/processed/mpr_in_data'
run_dir = '/work/kelbling/htcal_gen_mprin'

lut = lutreader.basin_lut('basin_lut_datagen.org')

thrshld_fac = 50000.0

os.makedirs(run_dir)

for station_id in lut.lut.keys():
    if float(lut.lut[station_id]['fac']) < thrshld_fac and lut.lut[station_id]['flag_calib']:
        print(f'Prepareing station: {station_id}')
        submit_job(run_dir, station_id, lut.lut[station_id]['basin'], mpr_dir, static_dir)

