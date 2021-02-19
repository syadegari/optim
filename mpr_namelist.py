from abstract_namelist import AbstractNameList
from typing import List


class MPRNameList(AbstractNameList):

    def __init__(self, namelist):
        super(MPRNameList, self).__init__(namelist)
        self.tag = 'mpr_global_parameter.nml'

    def __find__(self, kw):
        if kw in self.nml['parameters']['parameter_names']:
            return kw
        raise Exception(f'No {kw} where found in the given namelist file')

    def __getitem__(self, kw):
        path = self.__find__(kw)
        return dict(zip(self.nml['parameters']['parameter_names'], self.nml['parameters']['parameter_values']))[
            path]

    def __setitem__(self, kw, value):
        if not self.read_only:
            path = self.__find__(kw)
            index = self.nml['parameters']['parameter_names'].index(path)
            self.nml['parameters']['parameter_values'][index] = value
        else:
            raise Exception(f'The namelist is readonly')

    def get_all_model_parameters(self) -> List[str]:
        return self.nml['parameters']['parameter_names']
