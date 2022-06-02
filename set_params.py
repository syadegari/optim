from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
from spotpy_htcal_setup import modify_params, special_treatments
import f90nml as nml
import json
import argparse
import os


parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', help='Absolute path to nml file')
parser.add_argument('-j', '--json-file', help='Absolute path to param file')
args = parser.parse_args()

file_arg = args.file
param_file = args.json_file

file_path, _ = os.path.split(file_arg)
params = json.load(open(f'{param_file}'))['params'] 

mpr = MPRNameList(nml.read(file_arg))

mpr.read_only = False
for p, v in params.items():
    mpr[p] = v
mpr.read_only = True
mpr.write(path=file_path)


