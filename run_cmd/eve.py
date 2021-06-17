htessel = '''#!/bin/bash

set -e

module purge
module load foss/2018b
module load grib_api
module load netCDF-Fortran
echo "running htessel ..."
cd {dir_name}
for yy in $( seq {year_begin} {year_end} ); do
    cd ${{yy}}
    echo -n "    ${{yy}} - "
    ./htessel >> ../../htessel.log  2>&1
    echo "done"
    tail -n100 log_CaMa.txt > log_CaMa_clipped.txt
    rm log_CaMa.txt && mv log_CaMa_clipped.txt log_CaMa.txt 
    cd ..
done
echo "htessel done"
cd ..

find |grep o_wat| xargs rm
tail -n100 htessel.log > htessel_clipped.log
rm -f htessel.log && mv htessel_clipped.log htessel.log
'''

mpr = '''#!/bin/bash

set -e

module purge
module load foss/2019b
module load netCDF-Fortran
cd {dir_name}
echo "running mpr ..."
./mpr > ../mpr.log 2>&1
echo "mpr done"
cd ..

'''
