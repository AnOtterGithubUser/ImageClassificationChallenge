#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
path = "C:\\Users\\Thomas\\Desktop\\MVA 2016-2017\\2eme semestre\\Kernel methods for Machine learning\\Project\\kernel_challenge\\code"
os.chdir(path)
import numpy as np
import pandas as pd
import datetime
from kflearn import feature_extract

#%% Transform to greyscale function

def rgb_to_greyscale(dataset):
    columns_size = dataset.shape[1]
    if (columns_size % 3 != 0):
        raise ValueError('rgb_to_greyscale: column dimension must be a multiple of 3')
    channel_size = int(columns_size / 3)
    
    r = dataset[:,0:channel_size]
    g = dataset[:,channel_size:2*channel_size]
    b = dataset[:,2*channel_size:3*channel_size]
    return 0.299*r + 0.587*g + 0.114*b

#%% Load dataset

IMAGE_SIZE = 32
CHANEL_SIZE = IMAGE_SIZE * IMAGE_SIZE

#X_full = pd.read_csv('../data/Xtr.csv', header=None).as_matrix()[:, 0:-1]
#X_cnn_features = pd.read_csv('../data/Xtr_features_mycnn.csv', header=None).as_matrix()
#X_augmented = pd.read_csv('../data/augmented_X.csv',header=None).as_matrix()
#X_final = np.concatenate((X_full,X_augmented),axis=0)
X_train = pd.read_csv('../data/Xtr.csv', header=None).as_matrix()[:, 0:-1]
X_test = pd.read_csv('../data/Xte.csv', header=None).as_matrix()[:, 0:-1]
X_matlab_features = pd.read_csv('../data/X_features_kmeans.csv', header=None).as_matrix()

Y_full = pd.read_csv('../data/Ytr.csv').as_matrix()[:,1]
#Y_augmented = pd.read_csv('../data/augmented_Y.csv').as_matrix()[:,1]
#Y_final = np.concatenate((Y_full, Y_augmented),axis=0)
#%% K-means feature learning
rfSize = 6
nb_patches = 100000
nb_centroids = 100
nb_iter = 50
whitening = True
dim = [32,32,3]
stride = 1
eps = 10
eps_zca = 0.1
X_features = feature_extract.FeatureLearning(X_train,X_test,rfSize,nb_patches,nb_centroids,nb_iter,whitening,dim,stride,eps,eps_zca)

#%%
X_multi = X_features
# X_multi = X_cnn_features
#X_multi = rgb_to_greyscale(X_full)
Y_multi = Y_full
N = len(Y_multi)
#X_histo = sh.simple_histogram(X_full)
#Y_histo = Y_full

#%% Select classifiers

from sklearn.svm import SVC,LinearSVC
from mllib import svm
from importlib import reload

classifiers = {
        'sklearn': SVC(kernel='linear', degree=2, C=1.0),
#        'sklearn': LinearSVC(),
        'SMO OVO': svm.multiclass_ovo(C=1.0, kernel=svm.Kernel.linear(), tol=1.0, max_iter=5000),
               }

#%% Assess classifiers

import timeit
from sklearn.model_selection import train_test_split, KFold

scores = {classifier_name: [] for classifier_name, classifier in classifiers.items()}
times = {classifier_name: [] for classifier_name, classifier in classifiers.items()}

#X_train, X_test, y_train, y_test = train_test_split(X_histo, Y_histo, test_size=0.33)

for i, (train, test) in enumerate(KFold(n_splits=2, shuffle=True).split(range(len(Y_multi)))):
    X_train, X_test, y_train, y_test = X_multi[train], X_multi[test], Y_multi[train], Y_multi[test]

    for classifier_name, classifier in classifiers.items():
        print("%s - fit" % classifier_name)
        start = timeit.default_timer()
        classifier.fit(X_train, y_train)
        print("%s - predict\n" % classifier_name)
        scores[classifier_name].append(classifier.score(X_test, y_test))
        times[classifier_name].append(timeit.default_timer() - start)

for classifier_name in classifiers:    
    print("\n%s -- score:%s | time:%s" % 
          (classifier_name, np.mean(scores[classifier_name]), round(np.mean(times[classifier_name]),2)))