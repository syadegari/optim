import csv

class basin_lut():
    def __init__(self, path):
        self.lut = {}
        with open(path, mode='r') as infile:
            reader = csv.DictReader(filter(lambda row: row[0]=='|', infile), delimiter = "|")
            for row in reader:
                tmp = {fieldname.strip(): value.strip() for (fieldname, value) in row.items()
                       if fieldname != ''}
                tmp['flag_calib']=bool(tmp['flag_calib'])
                self.lut.update({tmp['basin']:tmp})

# x = basin_lut('basin_lut.org')
# x.lut['6333']

class param_lut():
    def __init__(self, path):
        self.lut = {}
        with open(path, mode='r') as infile:
            reader = csv.DictReader(filter(lambda row: row[0]=='|', infile), delimiter = "|")
            for row in reader:
                tmp = {fieldname.strip(): value.strip() for (fieldname, value) in row.items()
                       if fieldname != ''}
                tmp['flag_optimize']=bool(tmp['flag_optimize'])
                tmp['flag_mpr_parameter']=bool(tmp['flag_mpr_parameter'])
                self.lut.update({tmp['parameter']:tmp})

# x = param_lut('params.org')
# x.lut['zach_thetar_1']

