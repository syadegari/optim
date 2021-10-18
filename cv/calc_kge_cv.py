from path import Path
from utils import check_job_multiyear_finished, grep
import multiprocessing as mp
import os
import re
from itertools import repeat
import json
import argparse
#
import sys, inspect
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from kge_multiyear import kge_multiyear
#

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-p', '--path', 
                    help='path to CV folder')
parser.add_argument('-s', '--skip-days',
                    type=int,
                    default=365,
                    help='warmup days that are skipped when calculating KGE')
args = parser.parse_args()
#
# cv_folder = '../../single_basin_optim_2/cv'
cv_folder = args.path
skip_days = args.skip_days

def get_kge(st, sub_st, kges):
    with Path(f'{sub_st}/default_sim/{sub_st}'):
        if check_job_multiyear_finished('.'):
            st_num = re.match('station_(\d+)', sub_st)[1]
            kges[sub_st] = list(kge_multiyear(st_num, '.', skip_days))


with Path(cv_folder):
    sts_super = grep(os.listdir(), '.*station_\d+')
    kge_results = {st: None for st in sts_super}
    for st in sts_super:
        kges = mp.Manager().dict()
        with Path(st):
            sub_sts = grep(os.listdir(), '.*station_\d+')
            pool = mp.Pool(36)
            pool.starmap(get_kge, 
                         zip(repeat(st, len(sub_sts)),
                             sub_sts,
                             repeat(kges, len(sub_sts))))            
            kge_results[st] = dict(kges)
            pool.close()
            pool.join()
#
json.dump(kge_results, open(f'{cv_folder}/kges.json', 'w'), indent=4)
