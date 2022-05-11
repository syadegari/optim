import socket
import json
import pathlib

config = json.load(open((f'{pathlib.Path(__file__).parent.resolve()}/config.json')))
cluster_name = config['cluster'].lower()


def get_paths():
    if cluster_name == 'eve':
        import htcal_path_eve as htpath
    elif cluster_name == 'ecmwf':
        import htcal_path_ecmwf as htpath
    elif cluster_name == 'juwels':
        import htcal_path_juwels as htpath
    else:
        raise Error('cannot import paths, check if running')
    return htpath

def get_submitheader():
    if cluster_name == 'eve':
        def gen_header(time, run_path, mem, nnodes, jobname):
            header = '''#!/usr/bin/bash
#SBATCH --time={time}
#SBATCH --output={run_path}/LOG.run.%j.out
#SBATCH --error={run_path}/LOG.run.%j.err
#SBATCH --mem-per-cpu={mem}
#SBATCH --cpus-per-task={nnodes}
#SBATCH --export=ALL
#SBATCH --job-name={jobname}
        '''.format(
            time           = time,
            run_path       = run_path,
            basin          = str(basin),
            mem            = mem,
            path_pythonenv = path_pythonenv)
            return(header)
    elif cluster_name == 'ecmwf':
        def gen_header(time, run_path, mem, nnodes, jobname):
            if nnodes == 1:
                queue = 'ns'
            else:
                queue = 'nf'
            header = '''#!/usr/bin/ksh
#PBS -N {jobname}
#PBS -S /bin/ksh
#PBS -q {queue}
#PBS -j oe
#PBS -o {run_path}/LOG.{basin}.out
#PBS -l walltime={time}
#PBS -l EC_total_tasks=1
#PBS -l EC_threads_per_task={nnodes}
#PBS -l EC_memory_per_task={mem}
            '''.format(
                time           = time,
                run_path       = run_path,
                basin          = str(basin),
                mem            = mem,
                queue          = queue,
                path_pythonenv = path_pythonenv)
            return(header)
    elif cluster_name == 'juwels':
            header = '''#!/usr/bin/bash
#SBATCH --time={time}
#SBATCH --output={run_path}/LOG.run.%j.out
#SBATCH --error={run_path}/LOG.run.%j.err
#SBATCH --mem-per-cpu={mem}
#SBATCH --cpus-per-task={nnodes}
#SBATCH --export=ALL
#SBATCH --job-name={jobname}
        '''.format(
            time           = time,
            run_path       = run_path,
            basin          = str(basin),
            mem            = mem,
            path_pythonenv = path_pythonenv)
            return(header)
    else:
        raise Error(f'cannot create header, unknown cluster: {cluster_name}')
    return gen_header

class runcommand():
    def __init__(self, has_LAI_param : bool):
        self.has_LAI_param = has_LAI_param
        if cluster_name == 'eve':
            header_htessel = '''#!/bin/bash
set -e
module purge
module load foss/2018b
module load grib_api
module load netCDF-Fortran
                '''
            header_mpr = '''#!/bin/bash
set -e
module purge
module load foss/2019b
module load netCDF-Fortran
module load NCO
                '''
        elif cluster_name == 'ecmwf':
            header_htessel = '''#!/bin/bash
set -e
                '''
            header_mpr = '''#!/bin/bash
set -e
                '''

        elif cluster_name == 'juwels':
            print('not implemented yet')
        else:
            raise Error(f'cannot create script, unknown cluster: {cluster_name}')
        htessel_run = '''
echo "running htessel ..."
cd {dir_name}
for yy in $( seq {year_begin} {year_end} ); do
    cd ${{yy}}
    echo -n "    ${{yy}} - "
    ./htessel >> ../../htessel.log  2>&1
    echo "done"
    tail -n100 log_CaMa.txt > log_CaMa_clipped.txt
    rm log_CaMa.txt && mv log_CaMa_clipped.txt log_CaMa.txt 
    cd ..
done
echo "htessel done"
cd ..

find |grep o_wat| xargs rm
tail -n100 htessel.log > htessel_clipped.log
rm -f htessel.log && mv htessel_clipped.log htessel.log
        '''
        mpr_run_without_LAI = '''
cd {dir_name}
echo "running mpr ..."
./mpr > ../mpr.log 2>&1
echo "mpr done"
cd ..
'''
        mpr_run_with_LAI = '''
cd {dir_name}
echo "running mpr ..."
./mpr > ../mpr.log 2>&1
echo "mpr done"
ncrename -h -O -v Mlail_out,Mlail -v Mlaih_out,Mlaih mprin
ncks -A -v Mlail,Mlaih mprin surfclim
cd ..
'''
        self.header_htessel = header_htessel
        self.header_mpr = header_mpr
        self.htessel = header_htessel + htessel_run
        if self.has_LAI_param:
            self.mpr     = header_mpr + mpr_run_with_LAI
        else:
            self.mpr     = header_mpr + mpr_run_without_LAI

