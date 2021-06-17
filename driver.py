#!/usr/bin/env python

import argparse
import os.path
import spotpy
from spotpy.algorithms import dds
import spotpy_htcal_setup


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--control-file', 
    help="control file")
parser.add_argument('-n', '--num-sample',  
    help="number of samples")
parser.add_argument('-l', '--basin_lut', dest = 'basin_lut', default = 'basin_lut.org',
    help = "basin lut")
args = parser.parse_args()

control_file_path, _ = os.path.splitext(args.control_file)
assert os.path.isfile(f"{control_file_path}.py"),\
    f"Control file {control_file_path}.py was not found"
assert os.path.isfile(f"{args.basin_lut}"),\
    f"Control file {args.basin_lut} was not found"

spot_setup = spotpy_htcal_setup.spot_setup_htcal(control_file_path, args.basin_lut)

sampler = dds(spot_setup, dbname="htcal", save_sim=False)
sampler.sample(int(args.num_sample))
