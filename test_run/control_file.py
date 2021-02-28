
# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = 'zacharias'

# TODO: consider making 'warmup' optional (i.e. equal 0 on default)
training = {
    3269: {'year_begin': 1999, 'year_end': 2000, 'warmup': 60},
    6333: {'year_begin': 1999, 'year_end': 2000, 'warmup': 60}
}

validation = {}

#
#                    lower             upper             default
#

params = {
    "zach_thetar_1"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_1"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_2"   :   [-0.01,    0.01,    0.00],
    "zach_thetas_3"   :   [-0.50,    0.50,    0.00],
    "zach_thetas_4"   :   [ 0.00,    1.00,    0.50],
    "zach_thetas_5"   :   [-0.01,    0.01,    0.00],
    "zach_thetas_6"   :   [-0.50,    0.50,    0.00],
    "rtf2"            :   [269.0,    271.0,   270.0]
}



