path_grdc_data = "/data/esm/global_mod/data/processed/GRDC_time_series/"
path_grdc_alloc = "/work-local/yadegari/optim_Eve/ecfpy/suites/htcal/luts"

path_forcing = "/work-local/yadegari/optim_Eve/forcings"
path_static = "/data/htcal/data/processed/static/15min/ini_data"

path_aux_dir = "/work-local/yadegari/optim_Eve/aux"
path_soilgrid = "/work-local/yadegari/soilgrids"

path_execs = "/work-local/yadegari/optim_Eve/execs"

mpr_tf = 'zacharias'

training = {
    3269: {'year_begin': 1999, 'year_end': 2009},
    6333: {'year_begin': 1999, 'year_end': 2009}
}

validation = {}


# this variable can be "single" or "multiple"
forcing_files = 'single'
assert forcing_files == 'single' or forcing_files == 'multiple'


