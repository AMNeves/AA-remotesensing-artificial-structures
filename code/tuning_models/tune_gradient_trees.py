import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import xgboost as xgb
import time
from datetime import timedelta
from utils import metrics
from utils import data
from utils import visualization as viz
from scipy.stats import uniform
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score
from sklearn.metrics import recall_score
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import make_scorer
from sklearn.metrics import classification_report
from sklearn.model_selection import RandomizedSearchCV
from sklearn.model_selection import GridSearchCV


def model(dfs):
    
    train_size = int(19386625*0.05)
    X_train, y_train, X_test, y_test = data.load(
        train_size, normalize=False, balance=False, osm_roads=True)
        
    start = time.time()
    print(f'Tuning on {X_train.shape}')
    xgb_model = xgb.XGBClassifier()
    # brute force scan for all parameters
    # usually max_depth is 6,7,8
    # learning rate is around 0.05, but small changes may make big diff
    # tuning min_child_weight subsample colsample_bytree can have
    # much fun of fighting against overfit
    # n_estimators is how many round of boosting
    # finally, ensemble xgboost with multiple seeds may reduce variance
    n_trees = [1500]
    parameters = {'n_jobs': [4],
                  'tree_method': ['gpu_hist'],
                  'predictor': ['gpu_predictor'],
                  'gpu_id': [0],
                  'objective': ['multi:softmax'],
                  # params tuning
                  'learning_rate': uniform(0.001,0.3),  # `eta` value
                  'max_depth': [3, 5, 6, 8],
                  'min_child_weight': [1, 3, 5],
                  "gamma": [0, 1, 5],
                  'colsample_bytree': uniform(0.7,0.9),
                  'n_estimators': n_trees,
                  'max_delta_step': uniform(1,10),
                  'verbose': [1]}

    kappa_scorer = make_scorer(cohen_kappa_score)
    gs = RandomizedSearchCV(xgb_model, parameters, cv=3, scoring={
                            'recall_macro'}, refit='recall_macro', return_train_score=False, n_iter=25, verbose=1)
    gs.fit(X_train, y_train)

    print("Best parameters set found on development set: ")
    print()
    print(gs.best_params_)
    print()

    clf = gs.best_estimator_
    y_pred = clf.predict(X_test)

    kappa = cohen_kappa_score(y_test, y_pred)
    matrix = confusion_matrix(y_test, y_pred)
    print(f'Kappa: {kappa}')
    print(classification_report(y_test, y_pred))

    end = time.time()
    elapsed = end-start
    print("Run time: " + str(timedelta(seconds=elapsed)))

    #viz.plot_confusionmx(matrix)
    #viz.plot_gridcv(gs.cv_results_, ["kappa"], "n_estimators", 500, 2000)


def main(argv):
    model(None)


if __name__ == "__main__":
    main(sys.argv)
