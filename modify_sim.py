import f90nml as nml
from typing import Any, List
import os

from htessel_namelist import HTESSELNameList
from mpr_namelist import MPRNameList
from cama_namelist import CamaNameList
from abstract_namelist import AbstractNameList
from util import get_first_true


def _get_year_range(directory:str) -> List[int]:
    return [s for s in os.listdir(directory) if re.match('^\d{4}$', s)]


def _which_namelist(namelists:List[AbstractNameList],
                    param_name:str) -> AbstractNameList:
    '''which input file (htessel, cama or mpr) has the parameter'''
    which_index = [
        (param_name in namelist) for namelist in namelists
    ]
    if sum(which_index) == 0:
        raise Exception(f'{param_name} was not found')
    if sum(which_index) > 1:
        raise Exception(f'{param_name} was found in more than one input file')
    # only one in the which_index is True
    return get_first_true(which_index, namelists)


def _modify_params(namelists:List[AbstractNameList],
                   params:dict) -> None:
    for param_name, param_value in params.items():
        namelist = _which_namelist(namelists, param_name)
        namelist[param_name] = param_value


def _special_treatments(ht_namelist:HTESSELNameList) -> None:
    if ht_namelist.tag == 'input':
        ht_namelist['rez0ice'] = int(ht_namelist['rez0ice'])
    else:
        raise Exception('wrong namelist is passed in. Expecting htessel namelist')


def modify_sim_param(params:dict):
    '''
    ├── default_sim/sim
    │   ├── basin/station_3269   <= we are here
    │   │   ├── mpr
    │   │   └── run
    │   │       ├── 1999
    │   │       └── 2000
    |   |       └── 2001
                    ...
    '''
    year_range = _get_year_range('run')
    htessel_inputs = [HTESSELNameList(nml.read(f"run/{year}/input")) \
                      for year in year_range]
    mpr = MPRNameList(nml.read("mpr/mpr_global_parameter.nml"))
    for ht_input in htessel_inputs:
        ht_input.read_only, mpr.read_only = False, False
        _modify_params([ht_input, mpr], params)
        _special_treatments(ht_input)
        ht_input.read_only, mpr.read_only = True, True
        # write the changes
        ht_input.write()
        mpr.write()
