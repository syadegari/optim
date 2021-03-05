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
import glob

class dummy_ctrl():
    def __init__(self):
        self.params = {
            "zach_thetar_1" : [1.0, 0.00, 0.50],
            "zach_thetas_1" : [1.0, 0.00, 0.50],
            "zach_thetas_2" : [0.01, -0.01, 0.00],
            "zach_thetas_3" : [0.5, -0.50, 0.00],
            "zach_thetas_4" : [1.0, 0.00, 0.50],
            "zach_thetas_5" : [0.01, -0.01, 0.00],
            "zach_thetas_6" : [0.5, -0.50, 0.00],
            "zach_vga_1" : [10.0, -10.0, 0.00],
            "zach_vga_2" : [0.10, -0.10, 0.00],
            "zach_vga_3" : [0.50, -0.50, 0.0],
            "zach_vga_4" : [0.10, -0.10, 0.00],
            "zach_vga_5" : [10.0, -10.0, 0.00],
            "zach_vga_6" : [0.10, -0.10, 0.00],
            "zach_vga_7" : [0.50, -0.50, 0.00],
            "zach_vga_8" : [0.10, -0.10, 0.00],
            "zach_vgn_1" : [10.0, -10.0, 0.00],
            "zach_vgn_2" : [10.0, -10.0, 0.00],
            "zach_vgn_3" : [5.00, -5.00, 0.00],
            "zach_vgn_4" : [10.0, -10.0, 0.00],
            "zach_vgn_5" : [5.00, -5.00, 0.00],
            "zach_vgn_6" : [10.0, -10.0, 0.00],
            "zach_vgn_7" : [10.0, -10.0, 0.00],
            "zach_vgn_8" : [5.00, -5.00, 0.00],
            "zach_vgn_9" : [10.0, -10.0, 0.00],
            "zach_vgn_10" : [5.00, -5.00, 0.00],
            "rsnrttemp" : [3.002560e+02, 2.456640e+02, 2.729600e+02],
            "rtf1" : [2.760000e+02, 2.721000e+02, 2.741600e+02],
            "rtf2" : [2.720000e+02, 2.680000e+02, 2.701600e+02],
            "ralfmaxsn" : [9.350000e-01, 7.650000e-01, 8.500000e-01],
            "ralamsn" : [2.068000e+00, 1.692000e+00, 1.880000e+00],
            "ralfminsn" : [5.500000e-01, 4.500000e-01, 5.000000e-01],
            "rtauf" : [2.640000e-01, 2.160000e-01, 2.400000e-01],
            "rkerst3" : [1.100000e+00, 9.000000e-01, 1.000000e+00],
            "rsndtdestroi" : [1.650000e+02, 1.350000e+02, 1.500000e+02],
            "rsndtoverc" : [1.980000e-02, 1.620000e-02, 1.800000e-02],
            "rhominsna" : [1.199000e+02, 9.810000e+01, 1.090000e+02],
            "rsndtoverb" : [8.910000e-02, 7.290000e-02, 8.100000e-02],
            "rsnsnow" : [7.700000e+00, 6.300000e+00, 7.000000e+00],
            "rsndtovera" : [4.070000e+07, 3.330000e+07, 3.700000e+07],
            "rhominsnb" : [6.600000e+00, 5.400000e+00, 6.000000e+00],
            "rsminb" : [5.500000e+01, 4.500000e+01, 5.000000e+01],
            "rsigormin" : [1.100000e+02, 9.000000e+01, 1.000000e+02],
            "rlambdawat" : [6.270000e-01, 5.130000e-01, 5.700000e-01],
            "rsrdep" : [5.500000e-01, 4.500000e-01, 5.000000e-01],
            "rdsnmax" : [1.100000e+00, 9.000000e-01, 1.000000e+00],
            "rlwcswec" : [1.100000e-01, 9.000000e-02, 1.000000e-01],
            "rqexp" : [4.400000e-01, 3.600000e-01, 4.000000e-01],
            "rsnlargesn" : [5.500000e+01, 4.500000e+01, 5.000000e+01],
        }

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

basin_id = '6333'
base_dir = '/work/kelbling/htcal_optim/single_basin_optim' 
exp_dirs = ['8smallbasins_default', '8smallbasins_mean3maxdef', '8smallbasins_meanmindef',
            '8smallbasins_mean2maxdef', '8smallbasins_mean3mindef']

paths = [{'ctrl' : f'{base_dir}/{exp}/basin_{basin_id}/control_file.py',
          'bpath' : f'{base_dir}/{exp}/basin_{basin_id}',
          'res' : f'{base_dir}/{exp}/basin_{basin_id}/runs/res.txt'} for exp in exp_dirs]

param_sets = []

for ii in paths:
    sys.path.insert(0, ii['bpath'])
    # ctrl_file = __import__(ii['ctrl'])
    ctrl_file = dummy_ctrl()
    lines = open(ii['res']).readlines()
    param_sets.append((get_params(lines))[-1])

print(param_sets)

# ctrl_file = __import__(paths[0]['ctrl'])
ctrl_file = dummy_ctrl()
params_dict = ctrl_file.params
# add the parameters evolution to the list
for idx, k in enumerate(params_dict):
    params_dict[k] = {
        'boundaries': {'min': params_dict[k][0], 'max': params_dict[k][1], 'default': params_dict[k][2]},
        'vals': [float(set_[idx]) for set_ in param_sets]
    }


# argmax = np.array(kges).argmax()
# maxval = np.array(kges).max()
# fig, ax = plt.subplots(1, 1)
# ax.plot(kges)
# ax.set_title(f'KGE: best iteration, value = {argmax + 1}, {maxval:.6f}')
# ax.set_ylim(-0.41, 1)
# ax.plot([argmax], [kges[argmax]], 'o', color='b')
# fig.savefig(f'{run_folder}/KGE.png')


for param in params_dict:
    fig, ax = plt.subplots(1, 1)
    N = len(params_dict[param]['vals'])
    ax.plot(params_dict[param]['vals'])
    ax.plot(np.arange(N), N * [params_dict[param]['boundaries']['min']])
    ax.plot(np.arange(N), N * [params_dict[param]['boundaries']['max']])
    ax.set_title(f'param: {param}')
    fig.savefig(f'plots/{param}.png')

