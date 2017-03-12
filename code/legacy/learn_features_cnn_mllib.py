#%% Load DATA
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from mllib import svm, tools, nn, optim, loss

X = pd.read_csv('../data/Xtr.csv', header=None).as_matrix()[:, 0:-1].astype(np.float32)
y = pd.read_csv('../data/Ytr.csv').as_matrix()[:,1]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)

IM_SIZE = 32
X_train = X_train.reshape(-1, 3, IM_SIZE, IM_SIZE)
X_test = X_test.reshape(-1, 3, IM_SIZE, IM_SIZE)

#%% Score on training and test datasets

def score(algo):
    correct_train = 0
    total_train = 0
    N = X_train.shape[0]
    nb_batchs = int(N / batch_size)
    for i in range(nb_batchs):
        inputs = X_train[i*batch_size:(i+1)*batch_size,:]
        labels = y_train[i*batch_size:(i+1)*batch_size]
        outputs = algo(inputs)
        predicted = np.argmax(outputs.data, axis=1)
        total_train += len(labels)
        correct_train += (predicted == labels).sum()
    
    correct_test = 0
    total_test = 0
    N = X_test.shape[0]
    nb_batchs = int(N / batch_size)
    for i in range(nb_batchs):
        inputs = X_test[i*batch_size:(i+1)*batch_size,:]
        labels = y_test[i*batch_size:(i+1)*batch_size]
        outputs = algo(inputs)
        predicted = np.argmax(outputs.data, axis=1)
        total_test += len(labels)
        correct_test += (predicted == labels).sum()
    
    return round(100*correct_train/total_train,2), round(100*correct_test/total_test,2)

#%%

class MyNet(nn.Module):
    def __init__(self, depth_conv2=16):
        super().__init__()
        self.depth_conv2 = depth_conv2
        self.features = nn.Sequential(
            nn.Conv2d(3, 6, 5),
            nn.BatchNorm2d(6),
            nn.ReLU(),
            nn.MaxPool2d(2,2),
            nn.Conv2d(6, depth_conv2, 5),
            nn.BatchNorm2d(depth_conv2),
            nn.ReLU(),
            nn.MaxPool2d(2,2)
        )
        
        self.flatten = nn.Flatten()
        
        self.classifier = nn.Sequential(
            nn.Linear(16*5*5, 10)
#              nn.Linear(16*5*5, 120),
#              nn.ReLU(),
#              nn.Linear(120, 84),
#              nn.ReLU(),
#              nn.Linear(84, 10)
        )
    def forward(self, x):
        x = self.features(x)
        x = self.flatten(x)
        x = self.classifier(x)
        return x.reshape(x.shape[0],-1)

    def backward(self, output_grad):
        output_grad = self.classifier.backward(output_grad)
        output_grad = self.flatten.backward(output_grad)
        return self.features.backward(output_grad)    

    def step(self, optimizer):
        self.classifier.step(optimizer)
        self.features.step(optimizer)

    def zero_grad(self):
        self.classifier.zero_grad()
        self.features.zero_grad()

    def parameters(self):
        return self.features.parameters() + self.classifier.parameters()

#%%
mynet = MyNet(16)
#%% Train
from importlib import reload 
import timeit

#optimizer = optim.SGD(lr=0.001, momentum=0.9)
#optimizer = optim.Adam(lr=0.001)
#optimizer = optim.RMSprop(lr=0.001,lambda_reg=0.5)
optimizer = optim.RMSprop(lr=0.001)

#criterion = loss.CrossEntropyLossL2(lambda_reg=0.5)
criterion = loss.CrossEntropyLoss()

N = X_train.shape[0]
batch_size = 16
nb_batchs = int(N / batch_size)

start_global = timeit.default_timer()
optimizer._reset_state()
for epoch in range(0, 15, 1): # loop over the dataset multiple times
    running_loss = 0.0
    start = timeit.default_timer()
    suffle = np.random.permutation(N)
    X_train = X_train[suffle,:]
    y_train = y_train[suffle]
    for i in range(nb_batchs):
    #for i in np.random.permutation(nb_batchs):
        # get the inputs
        inputs = X_train[i*batch_size:(i+1)*batch_size,:]
        labels = y_train[i*batch_size:(i+1)*batch_size]
        # zero the parameter gradients
        mynet.zero_grad()
        # forward + backward + optimize
        outputs = mynet(inputs)
        curr_loss = criterion(outputs, labels)#, mynet.parameters())
        grad = criterion.grad(outputs, labels)
        mynet.backward(grad)  
        mynet.step(optimizer)
        # print statistics
        running_loss += curr_loss
        if i % 100 == 99: # print every 2000 mini-batches
            print('[{}, {}] - loss: {} | time: '.format(
                    epoch+1, i+1, round(running_loss / 100, 3)),
                    round(timeit.default_timer() - start, 2))
            running_loss = 0.0
            start = timeit.default_timer()
    if (epoch + 1) % 1 == 0:
        score_train, score_test = score(mynet)
        print('Accuracy -- Train: {} | Test: {}'.format(score_train, score_test))

print('Finished Training | {} seconds'.format(round(timeit.default_timer() - start_global, 2)))

#%%
Xout = X_train
N = Xout.shape[0]
X_features = np.empty((N, 400))
batch_size = 8
nb_batchs = int(N / batch_size)
for i in range(nb_batchs):
    inputs = Xout[i*batch_size:(i+1)*batch_size,:]
    outputs = mynet.features(inputs)
    X_features[i*batch_size:(i+1)*batch_size, :] = outputs.reshape(-1,16*5*5)
X_train_cnn = X_features.copy()
del Xout, X_features

Xout = X_test
N = Xout.shape[0]
X_features = np.empty((N, 400))
batch_size = 8
nb_batchs = int(N / batch_size)
for i in range(nb_batchs):
    inputs = Xout[i*batch_size:(i+1)*batch_size,:]
    outputs = mynet.features(inputs)
    X_features[i*batch_size:(i+1)*batch_size, :] = outputs.reshape(-1,16*5*5)
X_test_cnn = X_features.copy()
del Xout, X_features

#%%
from sklearn.svm import SVC
#clf = svm.multiclass_ovo(C=1000., kernel=svm.Kernel.rbf(gamma=1/50), tol=1.0, max_iter=5000)
clf = SVC(kernel='rbf', gamma=1/50, C=10.)
clf.fit(X_train_cnn, y_train)

print(clf.score(X_test_cnn, y_test))

#from sklearn.model_selection import train_test_split, KFold
#
#scores_train = {classifier_name: [] for classifier_name, classifier in classifiers.items()}
#scores_test = {classifier_name: [] for classifier_name, classifier in classifiers.items()}
#times = {classifier_name: [] for classifier_name, classifier in classifiers.items()}
#
##X_train, X_test, y_train, y_test = train_test_split(X_multi, Y_multi, test_size=0.33)
#
#for i, (train, test) in enumerate(KFold(n_splits=3, shuffle=True).split(range(len(Y_multi)))):
#    X_train, X_test, y_train, y_test = X_multi[train], X_multi[test], Y_multi[train], Y_multi[test]
#
#    for classifier_name, classifier in classifiers.items():
#        print("%s - fit" % classifier_name)
#        start = timeit.default_timer()
#        classifier.fit(X_train, y_train)
#        print("%s - predict\n" % classifier_name)
#        scores_train[classifier_name].append(classifier.score(X_train, y_train))
#        scores_test[classifier_name].append(classifier.score(X_test, y_test))
#        times[classifier_name].append(timeit.default_timer() - start)
#
#for classifier_name in classifiers:    
#    print("\n%s -- score: training:%s & test:%s | time:%s" % 
#          (classifier_name, np.mean(scores_train[classifier_name]), np.mean(scores_test[classifier_name]), round(np.mean(times[classifier_name]),2)))


