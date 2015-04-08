#!/bin/bash
# Ausführen:
# /home/pi/Dropbox/Seiloptimierung/SEILAPLAN/SeilaplanPlugin/backups+testFiles/testBash.sh

p="/home/pi/Dropbox/Seiloptimierung/SEILAPLAN/SeilaplanPlugin"
echo "Name of Dump:"
read s
echo "Name of Test Case:"
read t
d=`date +%y.%m.%d_%T`
f="$d-$t"
cd /home/pi/Dropbox/Seiloptimierung/SEILAPLAN/SeilaplanPlugin
python -m cProfile -o $f.prof STANDALONE.py $s
# python gprof2dot.py -f pstats 14.12.21_23:12:53-mittelNachOptiMainHOME.prof | dot -Tpng -o 14.12.21_23:12:53-mittelNachOptiMainHOME.png
python $p/backups+testFiles/gprof2dot.py -f pstats $f.prof | dot -Tpng -o $f.png
mv $p/$f.prof $p/backups+testFiles/$f.prof
mv $p/$f.png $p/backups+testFiles/$f.png
cd /home/pi/Dropbox/Seiloptimierung/SEILAPLAN/SeilaplanPlugin/backups+testFiles
python makeStats.py $f
