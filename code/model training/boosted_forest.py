"""
Created on Sun Mar  3 21:42:16 2019

@author: André Neves
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import matplotlib.pyplot as plt
import xgboost as xgb
from joblib import dump, load
from xgboost import plot_importance
from sklearn.metrics import classification_report, confusion_matrix, cohen_kappa_score
import gdal
from utils import data
from utils import visualization as viz
import time
from datetime import timedelta
import numpy as np
from sklearn.linear_model import LassoCV
from sklearn.feature_selection import SelectFromModel
from tqdm import tqdm

# inicialize data location
DATA_FOLDER = "../sensing_data/"
ROI = "vila-de-rei/"

DS_FOLDER = DATA_FOLDER + "clipped/" + ROI
OUT_RASTER = DATA_FOLDER + "results/" + ROI + \
    "/timeseries/boosted_20px_ts_s2_idx_roadstrack_align_classification.tiff"
OUT_PROBA_RASTER = DATA_FOLDER + "results/" + ROI + \
    "/timeseries/boosted_20px_ts_s2_idx_roadstrack_align_classification_proba_"

REF_FILE = DATA_FOLDER + "clipped/" + ROI + \
    "/ignored/static/clipped_sentinel2_B08.vrt"


def main(argv):
    train_size = int(19386625*0.2)
    X, y, X_test, y_test = data.load(
        train_size, normalize=False, balance=False, osm_roads=True)

    start = time.time()
    # Build a forest and compute the feature importances
    forest = xgb.XGBClassifier(colsample_bytree=0.5483193137202504,
                               gamma=0.1,
                               gpu_id=0,
                               learning_rate=0.6783980222181293,
                               max_depth=6,
                               min_child_weight=1,
                               n_estimators=1500,
                               n_jobs=4,
                               objective='multi:softmax',  # binary:hinge if binary classification
                               predictor='gpu_predictor',
                               tree_method='gpu_hist')

    print("Fitting data...")
    forest.fit(X, y)

    end = time.time()
    elapsed = end-start
    print("Training time: " + str(timedelta(seconds=elapsed)))

    y_pred = forest.predict(X_test)

    kappa = cohen_kappa_score(y_test, y_pred)
    print(f'Kappa: {kappa}')
    print(classification_report(y_test, y_pred))
    print(confusion_matrix(y_test, y_pred))

    importances = forest.feature_importances_
    indices = np.argsort(importances)[::-1]
    # Plot the feature importances of the forest
    plt.figure()
    plt.title("Feature importances")
    plt.bar(range(X.shape[1]), importances[indices],
            color="c", align="center")
    plt.xticks(range(X.shape[1]), data.feature_map(
        indices), rotation='90', horizontalalignment="right")
    plt.xlim([-1, X.shape[1]])
    plt.show()

    dump(forest, '../sensing_data/models/boosted.joblib')
    print("Saved model to disk")
    # Testing trash
    X, y, shape = data.load_prediction(
        ratio=1, normalize=False, osm_roads=True)

    start_pred = time.time()
    # batch test
    X_h = X[:len(X)//2]
    X_h1 = X[len(X)//2:]

    forest.get_booster().set_param('predictor', 'cpu_predictor')

    print("Predict 0%...")
    y_pred = forest.predict_proba(X_h)
    print("Predict 50%...")
    y_pred2 = forest.predict_proba(X_h1)
    print("Predict 100%...")

    y_pred_proba = np.concatenate((y_pred, y_pred2))
    y_pred_classes = np.array([ np.argmax(yi, axis=-1) + 1 for yi in tqdm(y_pred_proba)])

    kappa = cohen_kappa_score(y, y_pred_classes)
    print(f'Kappa: {kappa}')
    print(classification_report(y, y_pred_classes))
    print("Predict time: " + str(timedelta(seconds=time.time()-start_pred)))

    y_pred_classes_reshaped = y_pred_classes.reshape(shape)

    viz.createGeotiff(OUT_RASTER, y_pred_classes_reshaped, REF_FILE, gdal.GDT_Byte)

    print("Creating uncertainty matrix...")
    start_matrix = time.time()

    y_pred_proba_reshaped = y_pred_proba.reshape((shape[0], shape[1], 4))

    viz.createGeotiff(OUT_PROBA_RASTER + "estrutura.tiff",
                      y_pred_proba_reshaped[:, :, 0], REF_FILE, gdal.GDT_Float32)
    viz.createGeotiff(OUT_PROBA_RASTER + "estrada.tiff",
                      y_pred_proba_reshaped[:, :, 1], REF_FILE, gdal.GDT_Float32)
    viz.createGeotiff(OUT_PROBA_RASTER + "restante.tiff",
                      y_pred_proba_reshaped[:, :, 2], REF_FILE, gdal.GDT_Float32)
    viz.createGeotiff(OUT_PROBA_RASTER + "agua.tiff",
                      y_pred_proba_reshaped[:, :, 3], REF_FILE, gdal.GDT_Float32)

    end = time.time()
    elapsed = end-start_matrix
    print("Matrix creation time: " + str(timedelta(seconds=elapsed)))

    end = time.time()
    elapsed = end-start
    print("Total run time: " + str(timedelta(seconds=elapsed)))

if __name__ == "__main__":
    main(sys.argv)
