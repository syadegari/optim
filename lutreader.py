import csv
import sys
import copy

class basin_lut():
    def __init__(self, path):
        self.lut = {}
        with open(path, mode='r') as infile:
            reader = csv.DictReader(filter(lambda row: row[0]=='|', infile), delimiter = "|")
            for row in reader:
                tmp = {fieldname.strip(): value.strip() for (fieldname, value) in row.items()
                       if fieldname != ''}
                tmp['flag_calib']=(tmp['flag_calib'] == 'True')
                self.lut.update({tmp['basin']:tmp})

# x = basin_lut('basin_lut.org')
# x.lut['6333']

class param_lut():
    def __init__(self, path):
        self.lut = {}
        self.lut_bak = None
        with open(path, mode='r') as infile:
            reader = csv.DictReader(filter(lambda row: row[0]=='|', infile), delimiter = "|")
            for row in reader:
                tmp = {fieldname.strip(): value.strip() for (fieldname, value) in row.items()
                       if fieldname != ''}
                tmp['flag_optimize']=(tmp['flag_optimize'] == 'True')
                tmp['flag_mpr_parameter']=(tmp['flag_mpr_parameter'] == 'True')
                self.lut.update({tmp['parameter']:tmp})

    def reset_lut(self):
        if self.lut_bak is not None:
            self.lut = copy.deepcopy(self.lut_bak)
            self.lut_bak = None
        else:
            sys.exit('No backup lut available')

    def jitter_lut(self, wgt):
        wgt = float(wgt)
        if self.lut_bak is None:
            self.lut_bak = copy.deepcopy(self.lut)
            for _ , pp in self.lut.items():
                if pp['flag_optimize']:
                    if wgt < 0:
                        pp['default'] = (-wgt * float(pp['min']) + float(pp['default']))/(1-wgt)
                    else:
                        pp['default'] = (wgt * float(pp['max']) + float(pp['default']))/(1+wgt)
        else:
            sys.exit('Bak lut already exists')

    def print_lut(self):
        for _, pp in self.lut.items():
            if pp['flag_optimize']:
                print('         "{p_name}" : lower: {p_lower}, upper: {p_upper}, default: {p_default}'.format(
                    p_name    = pp['parameter'],
                    p_upper   = pp['min'],
                    p_lower   = pp['max'],
                    p_default = pp['default']
                ))


# x = param_lut('params.org')
# x.lut['zach_thetar_1']

