from abstract_namelist import AbstractNameList
from typing import List
from util import flatten


class CamaNameList(AbstractNameList):
    def __init__(self, namelist):
        super(CamaNameList, self).__init__(namelist)
        self.tag = 'input_cmf.nam'
        self.nml.uppercase = True
        self.paramsections = ["NDIMTIME",
                              "NFORCE"  ,
                              "NMAP"    ,
                              "NOUTPUT" ,
                              "NPARAM"  ,
                              "NRESTART",
                              "NRUNVER" ,
                              "NSIMTIME"]

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
