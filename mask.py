from typing import Dict, List
import f90nml as nml
from abstract_namelist import AbstractNameList
from util import is_list
from util import bcolors


def is_valid_range(list_two):
    return len(list_two) == 2 and list_two[0] <= list_two[1]


class ParamMask:

    def __init__(self, maskfile: str, namelist: AbstractNameList, default_threshold=0.2) -> None:
        self.maskfile = maskfile
        self.namelist = namelist
        self.mask_dict = self.read_mask()
        self.default_threshold = default_threshold

    def read_mask(self) -> Dict:
        try:
            return self.read_mask_generic()
        except IsADirectoryError:
            param_list = self.namelist.get_all_model_parameters()
            return {k: {'min': None, 'max': None} for k in param_list}

    def read_mask_generic(self) -> Dict:
        """
        Reads the mask file and returns a dictionary containing
         the names of parameters that will be used in sensitivity analysis:
        {name: str -> {'min': float/None, 'max': float/None}}
        If default is indicated, 'min' and 'max' are set to None, otherwise to
        their specified values.

        Returns
        -------

        """
        nmlist = nml.read(self.maskfile)
        d = {}
        for section in nmlist.keys():
            for subsection in nmlist[section]:
                if is_list(nmlist[section][subsection]) and is_valid_range(nmlist[section][subsection]):
                    d[subsection] = {'min': nmlist[section][subsection][0],
                                     'max': nmlist[section][subsection][1]}
                elif nmlist[section][subsection].lower() == 'default':
                    d[subsection] = {'min': None, 'max': None}
                else:
                    raise Exception(
                        f'key {subsection} in file {self.maskfile} does not have the correct format')
        return d

    def fill_none_values(self) -> None:
        """
        if 'min' and 'max' have None values, fill these keys with
        the default_value found in the namelist file (plus/minus) threshold/2

        Returns
        -------

        """
        for par_name in self.mask_dict:
            if self.mask_dict[par_name]['min'] is None:
                default_value = self.namelist[par_name]
                if default_value >= 0:
                    self.mask_dict[par_name]['min'] = (1. - self.default_threshold / 2) * default_value
                    self.mask_dict[par_name]['max'] = (1. + self.default_threshold / 2) * default_value
                else:
                    self.mask_dict[par_name]['min'] = (1. + self.default_threshold / 2) * default_value
                    self.mask_dict[par_name]['max'] = (1. - self.default_threshold / 2) * default_value

    def fill_default_values(self) -> None:
        """
        adds the default value to the dictionary of each parameter.
        after this, the dictionary contains all the information needed
        for the parameters.dat file:

        name : {'min': min_val, 'max': max_val 'default': default_val},

        where the default value is found in the namelist file

        Returns
        -------

        """
        for par_name in self.mask_dict:
            default_value = self.namelist[par_name]
            self.mask_dict[par_name]['default'] = default_value

    def _lower_bound_eq_default(self, param):
        if self.mask_dict[param]['min'] == self.mask_dict[param]['default']:
            print(bcolors.WARNING + 'Warning: ' + bcolors.ENDC +
                  f'min = default for {param}: {self.mask_dict[param]["default"]}.')

    def _upper_bound_eq_default(self, param):
        if self.mask_dict[param]['max'] == self.mask_dict[param]['default']:
            print(bcolors.WARNING + 'Warning: ' + bcolors.ENDC +
                  f'max = default for {param}: {self.mask_dict[param]["default"]}.')

    def _all_eq(self, param):
        if self.mask_dict[param]['min'] == self.mask_dict[param]['max'] == self.mask_dict[param]['default']:
            print(bcolors.WARNING + 'Warning: ' + bcolors.ENDC +
                  f'min = max = default for {param}: {self.mask_dict[param]["default"]}.')

    def check_values(self):
        for param in self.mask_dict:
            assert self.mask_dict[param]['min'] <= self.mask_dict[param]['default'] <= self.mask_dict[param]['max']
            self._all_eq(param)
            self._lower_bound_eq_default(param)
            self._upper_bound_eq_default(param)

    # @warn_after_first_call('Warning: .get_mask method is called more than once')
    def get_mask(self) -> Dict[str, Dict[str, float]]:
        """
        Gets the complete dictionary containing all the information needed for
        parameters.dat file. This is the main method of the class.

        Returns
        -------

        """
        self.fill_none_values()
        self.fill_default_values()
        self.check_values()
        return self.mask_dict
