# --------------------------------------------------
#  -- USER SETTINGS --------------------------------
# --------------------------------------------------
#  -- path to git repo 'optim' ---------------------
# path_aux_dir = "/work-local/yadegari/optim_Eve/aux"
path_aux_dir = "/work-local/kelbling/optim"
#  -- path to exe dir ------------------------------
# TODO: change path to mpr exe, to e.g. mpr_{mpr_tf}
# expects to contain:
# htessel exe, as: master1s.exe
# mpr exectuables in the subdir:
# mpr/{mpr_tf}/MPR-0.6.7 ({mpr_tf} is e.g. 'zacharias')
# path_execs = "/work-local/yadegari/optim_Eve/execs"
path_execs = "/work-local/kelbling/optim_htcal_exes"

# --------------------------------------------------
#  -- GLOBAL SETTINGS ------------------------------
# --------------------------------------------------
#  -- cluster specific paths -----------------------
path_grdc_data = "/data/esm/global_mod/data/processed/GRDC_time_series"
path_grdc_alloc = "/data/htcal/data/processed/luts"

path_forcing = "/data/htcal/data/processed//forcings"
path_static = "/data/htcal/data/processed/static/15min/ini_data"

path_soilgrid = "/data/htcal/data/processed/mpr_in_data"

# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = 'zacharias'

training = {
    3269: {'year_begin': 1982, 'year_end': 1983, 'warmup': 180},
    6333: {'year_begin': 1982, 'year_end': 1983, 'warmup': 180}
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



