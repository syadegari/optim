
# --------------------------------------------------
#  -- EXPERIMENT SETTINGS --------------------------
# --------------------------------------------------
mpr_tf = 'zacharias_res'

# TODO: consider making 'warmup' optional (i.e. equal 0 on default)
# year_end is inclusive
training = {
    3269: {'year_begin': 1999, 'year_end': 2001, 'warmup': 30},
    1892: {'year_begin': 1999, 'year_end': 2001, 'warmup': 30},
    # 6333: {'year_begin': 1999, 'year_end': 1999, 'warmup': 120},
    # 5294: {'year_begin': 1999, 'year_end': 1999, 'warmup': 120},
    # 3342: {'year_begin': 1999, 'year_end': 1999, 'warmup': 120}
}

validation = {}

penalty = {
    'rwrst'  : {'lambda': -100.0, 'min': 0.01, 'max': 0.03},
    'wsatm'  : {'lambda': -100.0, 'min': 0.35, 'max': 0.58},
    'vgalpha': {'lambda': -100.0, 'min': 0.03, 'max': 15.0},
    'nfac'   : {'lambda': -100.0, 'min': 1.10, 'max': 1.60}
}

#
#          lower             upper             default
#

params = {
    "thetar_1": [0.0, 1.0, 0.5],
    "thetar_2": [-0.01, 0.01, 0.0],
    "thetar_3": [-0.5, 0.5, 0.0],
    "thetar_4": [0.0, 1.0, 0.5],
    "thetar_5": [-0.01, 0.01, 0.0],
    "thetar_6": [-0.5, 0.5, 0.0],
    #
    "zach_thetas_1": [0.0, 1.0, 0.5],
    "zach_thetas_2": [-0.01, 0.01, 0.0],
    "zach_thetas_3": [-0.5, 0.5, 0.0],
    "zach_thetas_4": [0.0, 1.0, 0.5],
    "zach_thetas_5": [-0.01, 0.01, 0.0],
    "zach_thetas_6": [-0.5, 0.5, 0.0],
    #
    "zach_vga_1": [-10.0, 10.0, 0.0],
    "zach_vga_2": [-0.1, 0.1, 0.0],
    "zach_vga_3": [-0.5, 0.5, 0.0],
    "zach_vga_4": [-0.1, 0.1, 0.0],
    "zach_vga_5": [-10.0, 10.0, 0.0],
    "zach_vga_6": [-0.1, 0.1, 0.0],
    "zach_vga_7": [-0.5, 0.5, 0.0],
    "zach_vga_8": [-0.1, 0.1, 0.0],
    #
    "zach_vgn_1": [-10.0, 10.0, 0.0],
    "zach_vgn_2": [-10.0, 10.0, 0.0],
    "zach_vgn_3": [-5.0, 5.0, 0.0],
    "zach_vgn_4": [-10.0, 10.0, 0.0],
    "zach_vgn_5": [-5.0, 5.0, 0.0],
    "zach_vgn_6": [-10.0, 10.0, 0.0],
    "zach_vgn_7": [-10.0, 10.0, 0.0],
    "zach_vgn_8": [-5.0, 5.0, 0.0],
    "zach_vgn_9": [-10.0, 10.0, 0.0],
    "zach_vgn_10": [-5.0, 5.0, 0.0],
}
