import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import time
from datetime import timedelta
from utils import metrics
from utils import data
from utils import visualization as viz
from sklearn.metrics import make_scorer
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score
from sklearn.metrics import recall_score
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import classification_report
from sklearn.model_selection import RandomizedSearchCV
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier

def model(dfs):
    start = time.time()
    train_size = 100_000
    X_train, y_train, X_test, y_test, _, _, _ = data.load(train_size, datafiles=dfs, normalize=False, osm_roads=False, split_struct=False)

    N_s = [500, 1000, 1500, 2000]
    min_samples_leaf = [1, 2, 4]
    min_samples_split = [2, 3, 6, 8]

    tuning_params = {
        'max_depth': [75, 80, 130, None],
        'min_samples_leaf': min_samples_leaf,
        'min_samples_split': min_samples_split,
        'n_estimators': N_s,
        'n_jobs': [-1],
        'class_weight': ['balanced', None, 'balanced_subsample']
    }

    print(
        f'# Tuning hyper-parameters for Random forest on { X_train.shape[0] } samples')
    print()
    kappa_scorer = make_scorer(cohen_kappa_score)
    gs = RandomizedSearchCV(RandomForestClassifier(), tuning_params, cv=3, scoring={
                            'kappa': kappa_scorer}, refit='kappa', return_train_score=True,  n_iter=5, verbose=2)
    gs.fit(X_train, y_train)

    print("Best parameters set found on development set:")
    print()
    print(gs.best_params_)
    print()
    print(gs.best_score_)
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


def main(argv):
    model(None)


if __name__ == "__main__":
    main(sys.argv)
