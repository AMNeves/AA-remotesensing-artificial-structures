from tqdm import tqdm
import numpy
import gdal
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# inicialize data location
DATA_FOLDER = "../sensing_data/raw/timeseries/"
ROI = "arbitrary/"
MASK = "../vector_data/" + ROI + "ROI.shp"


SRC = DATA_FOLDER + ROI + "/s2/"
DST_FOLDER = "../sensing_data/" + "clipped/" + ROI + "ts/"


def main(argv):
    src_dss = [SRC + f for f in os.listdir(SRC) if ".zip" not in f]
    src_dss.sort()

    for idx, f in enumerate(tqdm(src_dss)):
        for f1 in os.listdir(f):
            if ".xml" not in f1:
                gdal.Warp(DST_FOLDER + str(idx) + 'clipped_' + f1.split(".")[
                          0] + ".tif", f + "/" + f1, dstSRS="EPSG:32629", resampleAlg="near", format="GTiff", xRes=10, yRes=10, cutlineDSName=MASK, cropToCutline=1)

if __name__ == "__main__":
    main(sys.argv)
