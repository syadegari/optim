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

    @abstractmethod
    def get_all_model_parameters(self) -> List[str]:
        raise NotImplemented

    def write(self, path='.'):
        self.nml.write(f"{path}/{self.tag}", force=True)
