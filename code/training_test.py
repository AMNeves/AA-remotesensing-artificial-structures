import numpy as np
import os
import gdal
from sklearn import metrics
from sklearn.ensemble import RandomForestClassifier
from PIL import Image
import cv2
import numpy as np
import matplotlib
import matplotlib.pyplot as plt 
plt.switch_backend('Qt4Agg') 

#inicialize data location
DATA_FOLDER = "../sensing_data/"
DS_FOLDER = DATA_FOLDER + "warped/"
LB_FOLDER = DATA_FOLDER + "labels/"

def createGeotiff(outRaster, data, geo_transform, projection):
    # Create a GeoTIFF file with the given data
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = data.shape
    rasterDS = driver.Create(outRaster, cols, rows, 1, gdal.GDT_Byte)
    rasterDS.SetGeoTransform(geo_transform)
    rasterDS.SetProjection(projection)
    band = rasterDS.GetRasterBand(1)
    band.WriteArray(data)
    dataset = None

outRaster = DATA_FOLDER + "results/classification.tiff"

bandsData = []
geo_transform = None
projection = None
for raster in DS_FOLDER:
    # Open raster dataset
    rasterDS = gdal.Open(raster, gdal.GA_ReadOnly)
    # Get spatial reference
    geo_transform = rasterDS.GetGeoTransform()
    projection = rasterDS.GetProjectionRef()

    # Extract band's data and transform into a numpy array
    band = rasterDS.GetRasterBand(1)
    bandsData.append(band.ReadAsArray())
    
bandsData = np.dstack(bandsData)
rows, cols, noBands = bandsData.shape

# Read vector data, and rasterize all the vectors in the given directory into a single labelled raster
rasterDS = gdal.Open(LB_FOLDER + "cos.tif")
rBand = rasterDS.GetRasterBand(1)
lblRaster = rBand.ReadAsArray()

# Prepare training data (set of pixels used for training) and labels
isTrain = np.nonzero(lblRaster)
trainingLabels = lblRaster[isTrain]
trainingData = bandsData[isTrain]

# Train a Random Forest classifier
classifier = RandomForestClassifier(n_jobs=4, n_estimators=10)
classifier.fit(trainingData, trainingLabels)

# Predict class label of unknown pixels
noSamples = rows*cols
flat_pixels = bandsData.reshape((noSamples, noBands))
result = classifier.predict(flat_pixels)
classification = result.reshape((rows, cols))

# Create a GeoTIFF file with the given data
createGeotiff(outRaster, classification, geo_transform, projection)

img = Image.open('randomForest.tiff')
img.save('randomForest.png','png')

#img = cv2.imread('randomForest.png')

gray_image = cv2.imread('randomForest.png')
cv2.imwrite('gray_image.png',gray_image)

hist,bins = np.histogram(gray_image.flatten(),256,[0,256])
cdf = hist.cumsum()

cdf_m = np.ma.masked_equal(cdf,0)
cdf_m = (cdf_m - cdf_m.min())*255/(cdf_m.max()-cdf_m.min())
cdf = np.ma.filled(cdf_m,0).astype('uint8')

img2 = cdf[img]
image_enhanced=img2
cv2.imwrite('randomForestEnhanced.png',image_enhanced)

#recalculate cdf
hist,bins = np.histogram(image_enhanced.flatten(),256,[0,256])
cdf = hist.cumsum()
cdf_normalized = cdf * hist.max()/ cdf.max()

plt.plot(cdf_normalized, color = 'b')
plt.hist(image_enhanced.flatten(),256,[0,256], color = 'r')
plt.xlim([0,256])
plt.legend(('cdf','histogram'), loc = 'upper left')
plt.savefig('histogram_enhanced_2.png')
plt.show()