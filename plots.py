#!/usr/bin/env python

import matplotlib
import matplotlib.pyplot as plt
import re
import sys
import pandas as pd
import pandas
import numpy as np
from pandas.plotting import table
import argparse
import os

def get_kge(lines):
    return [float(re.findall('kge:\s+(.+)$', y)[0]) for y in 
            filter(lambda x: re.findall('kge:', x), lines)]


def get_params(lines):
    return [re.findall('parameters:\s+\[(.+)\]', y)[0].split(',') for y in
            filter(lambda x: re.findall('parameters:', x), lines)]


def plot_table(ctrl_file):
    params = ctrl_file.params
    ax = plt.subplot(111, frame_on=False)
    ax.xaxis.set_visible(False) 
    ax.yaxis.set_visible(False) 

    df = pd.DataFrame(np.array([v for v in params.values()]).transpose()[:2], 'min max'.split(), list(params.keys()))

    table(ax, df)  # where df is your data frame
    plt.savefig(f'{run_folder}/table.png', dpi=600)



parser = argparse.ArgumentParser()
parser.add_argument('-c', '--control-file', 
    help="control file")
args = parser.parse_args()

assert os.path.isfile(f"{args.control_file}.py")
    
path = '.'
control_file = args.control_file
sys.path.insert(0, path)
ctrl_file = __import__(control_file)
#
run_folder = ctrl_file.runs_dir

lines = open(f"{path}/{run_folder}/res.txt").readlines()

kges = get_kge(lines)
param_sets = get_params(lines)

plot_table(ctrl_file)

params_dict = ctrl_file.params
# add the parameters evolution to the list
for idx, k in enumerate(params_dict):
    params_dict[k] = {
        'boundaries': {'min': params_dict[k][0], 'max': params_dict[k][1], 'default': params_dict[k][2]},
        'evolution': [float(set_[idx]) for set_ in param_sets]
    }


argmax = np.array(kges).argmax()
maxval = np.array(kges).max()
fig, ax = plt.subplots(1, 1)
ax.plot(kges)
ax.set_title(f'KGE: best iteration, value = {argmax + 1}, {maxval:.6f}')
ax.set_ylim(-0.41, 1)
ax.plot([argmax], [kges[argmax]], 'o', color='b')
fig.savefig(f'{run_folder}/KGE.png')


for param in params_dict:
    fig, ax = plt.subplots(1, 1)
    N = len(params_dict[param]['evolution'])
    ax.plot(params_dict[param]['evolution'])
    ax.plot([argmax], [params_dict[param]['evolution'][argmax]], 'o', color='b')    
    ax.plot(np.arange(N), N * [params_dict[param]['boundaries']['min']])
    ax.plot(np.arange(N), N * [params_dict[param]['boundaries']['max']])
    ax.set_title(f'param: {param}')
    fig.savefig(f'{run_folder}/{param}.png')

