import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import csv
from sklearn import preprocessing
from sklearn.linear_model import SGDClassifier
from sklearn import svm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import argparse
from tqdm import tqdm
import numpy as np
from datetime import timedelta
import time
from utils import visualization as viz
from utils import data
import gdal
from sklearn.metrics import classification_report, confusion_matrix, cohen_kappa_score
from xgboost import plot_importance
from joblib import dump, load
import xgboost as xgb
import matplotlib.pyplot as plt
from feature_selection import fselector
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.layers import Dense, Dropout, Activation
from tensorflow.keras.models import Sequential
import tensorflow as tf
from sklearn.utils import class_weight
from sklearn.neighbors import KNeighborsClassifier
from tensorflow.keras.callbacks import EarlyStopping

def write_to_file(line):
    with open('./finalrun_validation.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(line)

def get_Data(labels_test):
    train_size = int(19386625*0.2)
    X_train, y_train, X_test, y_test, X_val, y_val, normalizer = data.load(
        train_size, normalize=False, balance=False, osm_roads=(labels_test==4), split_struct=(labels_test==3))
    return X_train, y_train, X_val, y_val

def xgbc(X, y, X_test, y_test, dataset, labels, n_classes):
    boosted = xgb.XGBClassifier(colsample_bytree=0.7553707061597048,
                                gamma=5,
                                gpu_id=0,
                                learning_rate=0.2049732654267658,
                                max_depth=8,
                                min_child_weight=1,
                                max_delta_step=9.075685204314162,
                                n_estimators=1500,
                                n_jobs=-1,
                                objective='multi:softmax',
                                predictor='gpu_predictor',
                                tree_method='gpu_hist')

    print("Starting model training with sample size: " + str(X.shape[0]))
    print("Fitting XGB...")
    start = time.time()
    boosted.fit(X, y)
    end = time.time()
    traintime = end-start

    dump(boosted, f'../sensing_data/models/boosted_{dataset}_{labels}.joblib')
    print("Saved XGB to disk")

    print("Predicting...")
    start = time.time()
    pred = boosted.predict(X_test)
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(pred, y_test)
    for i in list(range(1, n_classes+1)):
        line = ['XGB', dataset, X.shape[0], labels, False, i, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X.shape[1]]
        write_to_file(line)

def forest(X, y, X_test, y_test, dataset, labels, n_classes):
    rforest = RandomForestClassifier(n_estimators=500,
                                    min_samples_leaf=4,
                                    min_samples_split=2,
                                    max_depth=130,
                                    class_weight='balanced',
                                    n_jobs=-1, verbose=1)
    print("Fitting RF...")
    start = time.time()
    rforest.fit(X, y)
    end = time.time()
    traintime = end-start

    dump(rforest, f'../sensing_data/models/forest_{dataset}_{labels}.joblib')
    print("Saved RF to disk")

    print("Predicting...")
    start = time.time()
    pred = rforest.predict(X_test)
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(pred, y_test)
    for i in list(range(1, n_classes+1)):
        line = ['RF', dataset, X.shape[0], labels, False, i, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X.shape[1]]
        write_to_file(line)

def svmc(X, y, X_test, y_test, dataset, labels, n_classes):
    sv = svm.SVC(C=6.685338321430641, gamma=6.507029881541734, class_weight='balanced')

    print("Fitting SVM...")
    # svm cant handle full training data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=20000, train_size=100_000, stratify=y)

    start = time.time()
    sv.fit(X_train, y_train)
    end = time.time()
    traintime = end-start

    dump(sv, f'../sensing_data/models/svm_{dataset}_{labels}.joblib')
    print("Saved SVC to disk")

    print("Predicting...")
    start = time.time()
    pred = sv.predict(X_test)
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(pred, y_test)
    for i in list(range(1, n_classes+1)):
        line = ['SVM', dataset, X_train.shape[0], labels, False, i, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X.shape[1]]
        write_to_file(line)

def sgdc(X, y, X_test, y_test, dataset, labels, n_classes):

    sgc = SGDClassifier(alpha=0.2828985957487874, class_weight='balanced', early_stopping=True,
                        l1_ratio=0.12293886358853467, loss='hinge', max_iter=1000, penalty='elasticnet', tol=0.001)
    if labels == 3:
        sgc = SGDClassifier(alpha=1e-05, class_weight='balanced', early_stopping=True,
                        l1_ratio=0.3879508123619403, loss='hinge', max_iter=1000, penalty='elasticnet', tol=0.001)
    if  labels == 1:
        sgc = SGDClassifier(alpha=1e-06, class_weight='balanced', early_stopping=True,
                        l1_ratio=0.5611522829923167, loss='hinge', max_iter=500, penalty='L2', tol=0.001)
    if  labels == 4:
        sgc = SGDClassifier(alpha=1e-05, class_weight='balanced', early_stopping=True,
                        l1_ratio=0.7751072005346229, loss='hinge', max_iter=500, penalty='elasticnet', tol=0.001)

    print("Fitting SGD...")
    start = time.time()
    sgc.fit(X, y)
    end = time.time()
    traintime = end-start

    dump(sgc, f'../sensing_data/models/sgd_{dataset}_{labels}.joblib')
    print("Saved XGB to disk")

    print("Predicting...")
    start = time.time()
    pred = sgc.predict(X_test)
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(pred, y_test)
    for i in list(range(1, n_classes+1)):
        line = ['SGD', dataset, X.shape[0], labels, False, i, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X.shape[1]]
        write_to_file(line)

def neural(X_train, y_train, X_test, y_test, dataset, labels, n_classes):
    input_shape = X_train.shape[1]

    y_train = y_train - 1
    y_test = y_test - 1

    class_weights = class_weight.compute_class_weight('balanced',
                                                      np.unique(y_train),
                                                      y_train)

    y_train_onehot = tf.keras.utils.to_categorical(y_train, num_classes=n_classes)

    dnn = Sequential()
    # Define DNN structure
    dnn.add(Dense(256, input_dim=input_shape, activation='relu'))
    dnn.add(Dense(512, input_dim=input_shape, activation='relu'))
    dnn.add(Dense(512, input_dim=input_shape, activation='relu'))
    dnn.add(Dropout(0.2))
    dnn.add(Dense(units=n_classes, activation='softmax'))

    dnn.compile(
        loss='categorical_crossentropy',
        optimizer='Adam',
        metrics=['accuracy']
    )
    dnn.summary()

    es = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=5, verbose=0, mode='auto')
    print("Fitting Keras DNN...")
    start = time.time()
    dnn.fit(X_train, y_train_onehot,
            epochs=32, validation_split=0.2, class_weight=class_weights, callbacks=[es])
    end = time.time()
    traintime = end-start

    # serialize model to YAML
    model_yaml = dnn.to_yaml()
    with open(f"../sensing_data/models/dnn_tf_{dataset}_{labels}.yaml", "w") as yaml_file:
        yaml_file.write(model_yaml)
    # serialize weights to HDF5
    dnn.save_weights(f"../sensing_data/models/dnn_tf_{dataset}_{labels}.h5")
    print("Saved DNN to disk")

    print("Predicting...")
    start = time.time()
    y_pred_onehot = dnn.predict(X_test)
    y_pred = [np.argmax(pred) for pred in y_pred_onehot]
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(y_pred, y_test)
    for i in list(range(0, n_classes)):
        line = ['DNN', dataset, X_train.shape[0], labels, False, i+1, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X_train.shape[1]]
        write_to_file(line)

def knn(X, y, X_test, y_test):
    neigh = KNeighborsClassifier(n_neighbors=3)

    print("Fitting SVM...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=20000, train_size=100_000, stratify=y)

    start = time.time()
    neigh.fit(X_train, y_train)
    end = time.time()
    traintime = end-start

    print("Predicting...")
    start = time.time()
    pred = neigh.predict(X_test)
    end = time.time()
    predtime = end-start

    kappa, report = get_metrics(pred, y_test)
    for i in list(range(0, n_classes)):
        line = ['KNN', dataset, X_train.shape[0], labels, False, i+1, report[str(i)]['precision'], report[str(
            i)]['recall'], report[str(i)]['f1-score'], kappa, traintime, predtime, 'None', X_train.shape[1]]
        write_to_file(line)
    
def get_metrics(y_pred, y_true):
    kappa = cohen_kappa_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, output_dict=True)
    return kappa, report

def run_test(dataset, labels, n_classes):
    X, y, X_test, y_test = get_Data(labels)

    xgbc(X, y, X_test, y_test, dataset, labels, n_classes)

    forest(X, y, X_test, y_test, dataset, labels, n_classes)

    print("Normalization for SVMs and DNN: Loading...")
    normalizer = preprocessing.Normalizer().fit(X)
    X = normalizer.transform(X)
    X_test = normalizer.transform(X_test)
    print("Done!")

    sgdc(X, y, X_test, y_test, dataset, labels, n_classes)

    svmc(X, y, X_test, y_test, dataset, labels, n_classes)

    neural(X, y, X_test, y_test, dataset, labels, n_classes)

    knn(X, y, X_test, y_test)

if __name__ == "__main__":
    # DATASET codes: static 1, timeseries(s1s2) 2, timeseries dem 3, timeseries dem canny edge 4
    # LABELS codes: estruturas 1, estrutura separada 3, estrada e estrutura 4
    # write_to_file(['MODEL', 'DATASET', 'SAMPLE', 'LABELS', 'ISROAD', 'CLASS', 'PRECISION', 'RECALL', 'F1SCORE', 'KAPPA', 'TRAINTIME', 'PREDICTTIME', 'FSELECTOR', 'NFEATURES'])

    dss = [1,2,3,4]
    
    lbs = [1,3,4]
    ncls = [3,5,4]

    dataset = 3

    X, y, X_test, y_test = get_Data(4)
    xgbc(X, y, X_test, y_test, 3, 4, 4)

    # for idx, label in enumerate(lbs):
    #     print(f"Running label test: {label}")
    #     run_test(dataset, label, ncls[idx])
    #run_test(dataset, lbs[0], ncls[0])
    print("Test ended.")