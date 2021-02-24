path_grdc_data = "/data/esm/global_mod/data/processed/GRDC_time_series/"
path_grdc_alloc = "/work-local/yadegari/optim_Eve/ecfpy/suites/htcal/luts"

path_forcing = "/work-local/yadegari/optim_Eve/forcings"
path_static = "/data/htcal/data/processed/static/15min/ini_data"

path_aux_dir = "/work-local/yadegari/optim_Eve/aux"
path_soilgrid = "/data/htcal/data/processed/mpr_in_data"

path_execs = "/work-local/yadegari/optim_Eve/execs"

mpr_tf = 'zacharias'

training = {
    3269: {'year_begin': 1999, 'year_end': 2000, 'warmup': 60},
    6333: {'year_begin': 1999, 'year_end': 2000, 'warmup': 60}
}

validation = {}


# this variable can be "single" or "multiple"
forcing_files = 'single'
assert forcing_files == 'single' or forcing_files == 'multiple'

params = {
    "zach_thetar_1"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_1"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_2"   :   [-0.01,    0.01,    0.00],
    "zach_thetas_3"   :   [-0.50,    0.50,    0.00],
    "zach_thetas_4"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_5"   :   [-0.01,    0.01,    0.00],
    "zach_thetas_6"   :   [-0.50,    0.50,    0.00],
    "rtf2"            :   [269.0,    270.0,   271.0]          
}



