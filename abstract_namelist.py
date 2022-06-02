from abc import ABC, abstractmethod
from typing import List
from f90nml import Namelist

class AbstractNameList(ABC):
    def __init__(self, namelist: Namelist, tag=''):
        self.nml = namelist
        self.tag = tag
        self.read_only = True

    @abstractmethod
    def __getitem__(self, kw):
        raise NotImplemented

    @abstractmethod
    def __setitem__(self, kw, value):
        raise NotImplemented

    @abstractmethod
    def __find__(self, kw):
        raise NotImplemented

    def __contains__(self, kw):
        try:
            _ = self.__find__(kw)
            return True
        except:
            return False

    @abstractmethod
    def get_all_model_parameters(self) -> List[str]:
        raise NotImplemented

    def write(self, path='.'):   #TODO: remove default path and check the code 
        self.nml.write(f"{path}/{self.tag}", force=True)
