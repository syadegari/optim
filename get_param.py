#!/usr/bin/env python

import argparse
from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
import f90nml as nml

def get_file(filename):
    if filename[-5:] == 'input':
        f = HTESSELNameList(nml.read(filename))
    else:
        f = MPRNameList(nml.read(filename))
    return f

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file')
parser.add_argument('-p', '--param-name')
args = parser.parse_args()

filename = args.file
param = args.param_name
f = get_file(filename)

print(f[param])
