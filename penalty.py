import numpy as np
import xarray as xr
# np.seterr(all='raise')


def scale(v, v_min, v_max):
    v_bar = 0.5 * (v_min + v_max)
    v -= v_bar
    v_min -= v_bar
    v_max -= v_bar

    if v_min <= v <= v_max:
        return 0.0
    elif v > v_max:
        return abs((v - v_max)/v_max)
    else:
        return abs((v - v_min)/v_min)
    
scale_v = np.vectorize(scale, excluded=['v_min', 'v_max'])


def penalty_basin(mprin, penalty_dict):
    error_penalty = {k: 0.0 for k in penalty_dict}
    for var_name in penalty_dict:
        var = mprin[var_name].to_masked_array()
        var_min, var_max = penalty_dict[var_name]['min'], penalty_dict[var_name]['max']
        penalty_coeff = penalty_dict[var_name]['lambda']
        val_scaled = scale_v(var, v_min=var_min, v_max=var_max)
        V = val_scaled.count()
        error_penalty[var_name] = penalty_coeff * val_scaled.sum()/V
    return error_penalty


def calculate_penalty_error(basins, penalty_dict, sim_path):
    # this is the error on all basins (averaged before it is sent back)
    penalties = {k: 0.0 for k in penalty_dict}   
    for basin_nr in basins:
        mprin_folder_path = f"{sim_path}/basin_{basin_nr}/mpr/"
        error_basin = penalty_basin(get_mprin(mprin_folder_path), penalty_dict)
        for k in penalty_dict:
            penalties[k] += error_basin[k]
    return {k : v / len(basins) for k, v in penalties.items()}

def get_mprin(mprin_folder_path):
    print(f'opening {mprin_folder_path}/mprin')
    arr = xr.open_dataset(f'{mprin_folder_path}/mprin')
    arr.close()
    return arr
    
