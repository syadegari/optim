from lutreader import basin_lut


# runtime per flow accumulation [s]

# basin 1892 approx:
# rt_fac=65/3490.8
# basin 25 approx:
# mpr done

# real    3m33.174s
# user    3m0.055s
# sys     0m25.596s
# htessel done

# real    29m26.991s
# user    132m54.842s
# sys     49m31.481s
rt_fac=2010/783814.3

# upper bound runtime [s]
run_max=600

# upper bound fac:
max_fac=run_max/rt_fac

stations_dict=(basin_lut('basin_lut.org')).lut

# for each basin select only the station with the highest flow accumulation
basin_dict={}
for grdc_ii in stations_dict.keys():
    basin_ii = stations_dict[grdc_ii]['basin']
    if basin_ii in basin_dict.keys():
        if basin_dict[basin_ii]['fac'] < float(stations_dict[grdc_ii]['fac']):
            basin_dict.update({basin_ii : {'grdc_id' : grdc_ii, 'fac' : float(stations_dict[grdc_ii]['fac'])}})
    else:
        basin_dict.update({basin_ii : {'grdc_id' : grdc_ii, 'fac' : float(stations_dict[grdc_ii]['fac'])}})

# for ii in basin_dict.keys():
#     print(ii)
#     print(basin_dict[ii])

small_basin_dict = {}
for ii, jj in basin_dict.items():
    if float(jj['fac']) < max_fac:
        small_basin_dict.update({ii:jj})

print(small_basin_dict.keys())
print(len(small_basin_dict.keys()))
# for ii in small_basin_dict.keys():
#     print(ii)
    # print(basin_dict[ii])

