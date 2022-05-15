import os
from path import Path
import re
from functools import partial, reduce
from dataclasses import dataclass
from typing import List, Any, Tuple
import ntpath
import sys
import copy




def compose(*functions):
    def compose2(f, g):
        return lambda x: f(g(x))
    return reduce(compose2, functions, lambda x: x)


tail = lambda x, n=50: x[-n:]
head = lambda x, n=50: x[:n]


def readlines(path_to_file:str) -> list:
    with open(path_to_file) as fh:
        return fh.readlines()


def grep(lines:list, regex:str) -> list:
    reg = re.compile(regex)
    return [l for l in lines if re.match(reg, l)]


def diagnose_mpr(path_to_sim) -> str:
    raise NotImplemented


def diagnose_htessel(path_to_sim) -> str:
    raise NotImplemented


def check_mpr_finished(path_to_sim) -> bool:
    with Path(path_to_sim):
        if not os.path.exists('mpr.log'): return False
        if not os.path.exists('mpr/mprin'): return False
        res = compose(
            partial(grep, regex='.+MPR: Finished!'),
            partial(tail, n=1),
            readlines)('mpr.log')
        if res == []: return False
        return True


def check_htessel_multiyear_finished(path_to_sim) -> bool:
    with Path(path_to_sim):
        if not os.path.exists('htessel.log'): return False
        res = compose(
            partial(grep, regex='MASTER1s: Time total:'),
            partial(tail, n=1),
            readlines)('htessel.log')
        if res == []: return False
        with Path('run'):
            for yr in grep(os.listdir(), '\d{4}'):
                yr_files = os.listdir(yr)
                if not 'o_rivout_cmf.nc' in yr_files: return False
        return True


def check_job_multiyear_finished(path_to_sim: str) -> bool:
    return check_mpr_finished(path_to_sim) and check_htessel_multiyear_finished(path_to_sim)


def flatten(l):
    return [item for sublist in l for item in sublist]


def is_list(list_two):
    return type(list_two) == list


def merge_dict(dict1: dict, dict2: dict) -> dict:
    d = {}
    d.update(dict1)
    d.update(dict2)
    return d


def warn_after_first_call(msg):
    def f(func):
        setattr(func, 'counter', 0)
        def g(*args, **kwargs):
            func.counter += 1
            if func.counter > 1:
                print(msg)
            return func(*args, **kwargs)
        return g
    return f


@dataclass
class bcolors:
    '''https://stackoverflow.com/questions/287871/how-to-print-colored-text-in-python'''
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_first_true(true_list:List[bool],
                    obj_list:List[Any]) -> Any:
    return next(pair for pair in zip(true_list, obj_list) if pair[0])[1]


def import_control_file(control_file:str) -> Tuple[Any, str, str]:
    '''
    control_file: path to control file including the name of the control file
    returns:
        control_file: module of control file
        cf_path: path to control file not including the file
        cf_file: name of the control file without extention
        
    
    cf, cf_path, cf_name = import_control_file(control_file_path)
    '''
    control_file_path, _ = os.path.splitext(control_file)
    
    assert os.path.isfile(f"{control_file_path}.py"),\
    f"Control file {control_file_path}.py was not found"
    
    cf_path, cf_file = ntpath.split(control_file_path)
    
    sys_path_before_insert = copy.deepcopy(sys.path)
    sys.path.insert(0, cf_path)
    control_file = __import__(cf_file)
    sys.path = sys_path_before_insert
    
    return control_file, cf_path, cf_file
