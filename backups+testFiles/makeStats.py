# -*- coding: utf-8 -*-

import sys
import pstats

def main(inputname):
    path = "/home/pi/Dropbox/Seiloptimierung/SEILAPLAN/SeilaplanPlugin/backups+testFiles/{}".format(inputname)
    inputFile = path + ".prof"
    s1 = pstats.Stats(inputFile, stream=sys.stdout)
    s1.strip_dirs()
    s1.sort_stats('cumtime')
    s1.print_stats(30)

if __name__ == "__main__":
    #name = '14.12.15_17:45:53-lang'
    name = sys.argv[1]
    main(name)




