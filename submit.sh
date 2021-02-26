#!/usr/bin/bash

#SBATCH --time=08:00:00
#SBATCH --output=~/LOG.run.%j.out
#SBATCH --error=~/LOG.run.%j.err
#SBATCH --mem-per-cpu=16G
#SBATCH --export=ALL

python ./driver.py -c /test_run/control_file.py -n 10
