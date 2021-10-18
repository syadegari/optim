import os
from path import Path
import re
from functools import partial, reduce

def compose(*functions):
    def compose2(f, g):
        return lambda x: f(g(x))
    return reduce(compose2, functions, lambda x: x)


tail = lambda x, n=50: x[-n:]
head = lambda x, n=50: x[:n]


def readlines(path_to_file) -> list:
    with open(path_to_file) as fh:
        return fh.readlines()

def grep(lines:list, regex:str):
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
