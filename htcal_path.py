import socket

def check_eve(word):
    if '.' in word:
        word = word[-10:]
    return word in ['frontend1', 'frontend2', 'eve.ufz.de', 'datascience1']

def check_ecmwf(word):
    return word[:3] in ['cca', 'ccb'] or word in ['ecgb11']

def check_jules(word):
    return False

def get_paths():
    socketname = socket.gethostname()
    print(f'setting up paths for: {socketname}')
    if check_eve(socketname):
        import htcal_path_eve as htpath
    elif check_ecmwf(socketname):
        import htcal_path_ecmwf as htpath
    elif check_jules(socketname):
        import htcal_path_juwels as htpath
    else:
        raise Error('cannot import paths, check if running')
    return htpath

def get_submitheader():
    socketname = socket.gethostname()
    if check_eve(socketname):
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
    elif check_ecmwf(socketname):
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
    elif check_jules(socketname):
        print('not implemented yet')
    else:
        raise Error('cannot create header, unknown cluster: {socketname}')
    return gen_header

class runcommand():
    def __init__(self):
        socketname = socket.gethostname()
        if check_eve(socketname):
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
                '''
        elif check_ecmwf(socketname):
            header_htessel = '''#!/bin/bash
set -e
                '''
            header_mpr = '''#!/bin/bash
set -e
                '''
        elif check_jules(socketname):
            print('not implemented yet')
        else:
            raise Error('cannot create script, unknown cluster: {socketname}')
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
        mpr_run = '''
cd {dir_name}
echo "running mpr ..."
./mpr > ../mpr.log 2>&1
echo "mpr done"
cd ..
'''
        self.htessel = header_htessel + htessel_run
        self.mpr     = header_mpr + mpr_run

