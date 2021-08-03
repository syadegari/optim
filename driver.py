#!/usr/bin/env python

import argparse
import os.path
import spotpy
from spotpy.algorithms import dds
from spotpy_htcal_setup import spot_setup_htcal

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-c', '--control-file', 
                    help="control file, including the path")
parser.add_argument('-n', '--num-sample',  
                    type=int, help="number of samples")
parser.add_argument('-l', '--basin_lut', 
                    dest = 'basin_lut', default = 'basin_lut.org',
                    help = "basin lut")
parser.add_argument('--clean-completed', dest='clean_completed',
                    action='store_true', default=False,
                    help='clean each completed simulation or not')
args = parser.parse_args()

control_file_path, _ = os.path.splitext(args.control_file)
assert os.path.isfile(f"{control_file_path}.py"),\
    f"Control file {control_file_path}.py was not found"
assert os.path.isfile(f"{args.basin_lut}"),\
    f"Control file {args.basin_lut} was not found"

spot_setup = spot_setup_htcal(control_file_path, args.clean_completed, args.basin_lut)

sampler = dds(spot_setup, dbname="htcal", save_sim=False)
sampler.sample(int(args.num_sample))
