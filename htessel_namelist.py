from abstract_namelist import AbstractNameList
from typing import List
from util import flatten


class HTESSELNameList(AbstractNameList):
    """
    >>> import f90nml as nml
    >>> from copy import deepcopy

    >>> htessel = HTESSELNameList(nml.read(path_to_input))
    >>> htessel = HTESSELNameList(deepcopy(nml.read(path_to_input)))   # if we want to modify

    # get the values of a parameter
    >>> htessel[kw] -> returns the values of kw

    # set the value of a parameter
    >>> htessel.read_only = False
    >>> htessel[kw] = val
    >>> htessel.read_only = True
    """
    def __init__(self, namelist, param_sections="default"):
        super(HTESSELNameList, self).__init__(namelist)
        self.tag = 'input'
        self.nml.uppercase = True
        assert param_sections == 'default' or param_sections == 'all'
        if param_sections == 'default':
            self.paramsections = ['NAMPARAGS', 'NAMPARFLAKE',
                                  'NAMPARSNOW', 'NAMPARSOIL', 'NAMPARVEG']
        elif param_sections == 'all':
            self.paramsections = ["NAM1S"      ,     
                                  "NAMCT01S"   ,     
                                  "NAMDIM"     ,     
                                  "NAMDYN1S"   ,     
                                  "NAMFORC"    ,     
                                  "NAMPHY"     ,     
                                  "NAMPHYOFF"  ,     
                                  "NAMRIP"     ,     
                                  "NAMPARAGS"  ,     
                                  "NAMPAREXC"  ,     
                                  "NAMPARFLAKE",     
                                  "NAMPARSNOW" ,     
                                  "NAMPARSOIL" ,     
                                  "NAMPARVEG"]    

    def __find__(self, kw):
        for section_name in self.nml.keys():
            for subsection_name in self.nml[section_name]:
                if subsection_name == kw.lower():
                    return [section_name, subsection_name]
        raise Exception(f'No {kw} where found in the given namelist file')

    def __getitem__(self, kw):
        path1, path2 = self.__find__(kw)
        return self.nml[path1][path2]

    def __setitem__(self, kw, value):
        if not self.read_only:
            path1, path2 = self.__find__(kw)
            self.nml[path1][path2] = value
        else:
            raise Exception(f'The namelist is readonly')

    def get_all_model_parameters(self) -> List[str]:
        l = []
        for name in self.nml.keys():
            if name.upper() in self.paramsections:
                l.append(list(self.nml[name].keys()))
        return flatten(l)
