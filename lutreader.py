import csv
import os
import sys
import copy

class basin_lut():
    def __init__(self, path):
        self.lut = {}
        self.basins = []
        self.header = ''
        self.lut_path = path
        self.table_header = None
        self.col_widths = None
        with open(path, mode='r') as infile:
            line = infile.readline()
            while line and not line[0] == '|':
                self.header += line + '\n'
                line = infile.readline()
        with open(path, mode='r') as infile:
            reader = csv.DictReader(filter(lambda row: row[0]=='|', infile), delimiter = "|")
            for row in reader:
                tmp = {fieldname.strip(): value.strip() for (fieldname, value) in row.items()
                       if fieldname != ''}
                tmp['flag_calib']=(tmp['flag_calib'] == 'True' or tmp['flag_calib'] == 1 or
                                   tmp['flag_calib'] == '1' or tmp['flag_calib'] == 'true')
                if self.table_header is None:
                    self.table_header = list(tmp.keys())
                    self.col_widths = [len(xx) for _, xx in row.items()]
                self.lut.update({tmp['grdc_id']:tmp})
                if tmp['basin'] not in self.basins:
                    self.basins.append(tmp['basin'])

    def print_grdc_list(self):
        out_list = []
        for ii in self.lut:
            if bool(self.lut[ii]['flag_calib']):
                out_list.append(self.lut[ii]['grdc_id'])
        print(' '.join(out_list))

    def get_ids(self, some_id):
        if str(some_id) in list(self.lut.keys()):
            return([self.lut[str(some_id)]['basin'], str(some_id)])
        else:
            return([str(some_id), None])

    def write_lut(self):
        csv.register_dialect('org',
                             delimiter = '|',
                             lineterminator = '|\n',
                             skipinitialspace = False
        )
        def preproc_row(row_data, col_widths):
            """Return list of strings, with modified column widths
            `col_width` is list of integer column widths and an leding empty string
            for org format
            a bit messy, list for header, dict for other rows
            """
            if isinstance(row_data, dict):
                return [''] + [ '{0:<{width}}'.format(d, width=width) for
                        (d, width) in zip(list( row_data.values() ), col_widths[1:]) ]
            elif isinstance(row_data, list):
                return [ '{0:<{width}}'.format(d, width=width) for
                        (d, width) in zip(list( row_data ), col_widths) ]
        tempfilename = os.path.splitext(self.lut_path)[0] + '.bak'
        try:
            os.remove(tempfilename)  # delete any existing temp file
        except OSError:
            pass
        os.rename(self.lut_path, tempfilename)
        # create updated version of file
        with open(self.lut_path, mode='w') as outfile:
            outfile.write(self.header)
            writer = csv.writer(outfile, dialect = 'org')
            writer.writerow(preproc_row([''] + self.table_header, self.col_widths))
            for row in self.lut.values():
                writer.writerow(preproc_row(row, self.col_widths))

        # os.remove(tempfilename)  # delete backed-up original

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

    def decrease_interval(self, frac):
        if self.lut_bak is None:
            self.lut_bak = copy.deepcopy(self.lut)
            for _ , pp in self.lut.items():
                if pp['flag_optimize']:
                    # pp['min'] = float(pp['min']) + frac * (float(pp['default']) - float(pp['min']))
                    # pp['max'] = float(pp['min']) - frac * (float(pp['max']) + float(pp['default']))
                    # min and max are somehow wrong i.e. max is min and vice versa...
                    pp['min'] = float(pp['min']) - frac * (float(pp['min']) - float(pp['default']) )
                    pp['max'] = float(pp['max']) + frac * (float(pp['default']) - float(pp['max']))
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

