#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 17 10:29:39 2017

@author: EmileMathieu
"""
from .im2col import im2col_indices, col2im_indices
import numpy as np

class Module(object):
     def forward(self, X):
         raise NotImplementedError()
     def __call__(self, X):
         return self.forward(X)
     def backward(self, x):
         raise NotImplementedError()

     def step(self, optimizer):
         self._bias = optimizer(id(self), 'bias', self._bias, self._grad_bias)
         self._weight = optimizer(id(self), 'weight', self._weight, self._grad_weight)

     def zero_grad(self):
         self._grad_bias = None
         self._grad_weight = None

class ReLU(Module):
    def func(self, X):
         return np.maximum(X, 0)

    def forward(self, X):
        self._last_input = X
        return self.func(X)

    def backward(self, output_grad):
        return output_grad * self.func(self._last_input)

class MaxPool2d(Module):
    def __init__(self,kernel_size,stride=2):
         # TODO: add padding ?
         self._kernel_size = kernel_size
         self._stride = stride

    def forward(self, X):
         N,d,h,w = X.shape
         self._X_shape = N,d,h,w
         h_out = int((h - self._kernel_size)/self._stride + 1)
         w_out = int((w - self._kernel_size)/self._stride + 1)

         # Im2Col approach http://wiseodd.github.io/techblog/2016/07/18/convnet-maxpool-layer/
         X_reshaped = X.reshape(N*d, 1, h, w)
         X_col = im2col_indices(X_reshaped, self._kernel_size, self._kernel_size, padding=0, stride=self._stride)
         max_idx = np.argmax(X_col, axis=0)
         self._max_idx = max_idx
         res = X_col[max_idx, range(max_idx.size)]
         res = res.reshape(h_out, w_out, N, d)
         res = res.transpose(2, 3, 0, 1)

#         res = np.empty((N, d, h_out, w_out))
#         for i, x in enumerate(X):
#             res[i,:] = np.max([x[:,(i>>1)&1::2,i&1::2] for i in range(4)],axis=0) #fastest
#             #res[i,:] = x.reshape(d, int(h/2), 2, int(w/2), 2).max(axis=(2, 4)) #2sd fastest
         return res

    def backward(self, output_grad):
        N,d,h,w = self._X_shape
        kernel_area = self._kernel_size*self._kernel_size
        dX_col = np.zeros((kernel_area, int(N*d*h*w/kernel_area)))
        dout_flat = output_grad.transpose(2, 3, 0, 1).ravel()
        dX_col[self._max_idx, range(self._max_idx.size)] = dout_flat
        dX = col2im_indices(dX_col, (N * d, 1, h, w), self._kernel_size, self._kernel_size, padding=0, stride=self._stride)
        return dX.reshape(self._X_shape)

class Conv2d(Module):
    def __init__(self,in_channels, out_channels, kernel_size, stride=1, padding=0):
         self._in_channels = in_channels
         self._out_channels = out_channels
         self._kernel_size = kernel_size
         self._stride = stride
         self._padding = padding
         law_bound = 1/np.sqrt(kernel_size*kernel_size*in_channels)
         self._bias = np.random.uniform(-law_bound,law_bound,size=(out_channels)).astype(np.float32)
         self._weight = np.random.uniform(-law_bound,law_bound,size=(out_channels, in_channels, kernel_size, kernel_size)).astype(np.float32)

    def forward(self, X):
        N,d,h,w = X.shape
        self._X_shape = N,d,h,w
        n_filters = self._weight.shape[0]
        h_out = int((h - self._kernel_size + 2*self._padding) / self._stride + 1)
        w_out = int((w - self._kernel_size + 2*self._padding) / self._stride + 1)

        # Im2Col approach: http://wiseodd.github.io/techblog/2016/07/16/convnet-conv-layer/
        # (https://leonardoaraujosantos.gitbooks.io/artificial-inteligence/content/making_faster.html)
        X_col = im2col_indices(X, self._kernel_size, self._kernel_size, padding=self._padding, stride=self._stride)
        self._X_col = X_col
        W_col = self._weight.reshape(n_filters, -1)
        res = W_col @ X_col
        res = res + np.tile(self._bias, (res.shape[1],1)).T
        res = res.reshape(n_filters, h_out, w_out, N)
        res = res.transpose(3, 0, 1, 2)

#        res = np.empty((N, self._out_channels, h_out, w_out))
#        #for n, x in enumerate(X):
#            for f,bias in enumerate(self._bias):
#                res[n, f, :] = bias + np.sum([scipy.ndimage.filters.correlate(x[i], self._weight[f][i], mode='constant')[2:-2,2:-2] for i in range(d)], axis=0)
        return res

    def backward(self, output_grad):
        n_filters = self._weight.shape[0]

        self._grad_bias = np.sum(output_grad, axis=(0, 2, 3))

        output_grad_reshaped = output_grad.transpose(1, 2, 3, 0).reshape(n_filters, -1)
        grad_weight = output_grad_reshaped @ self._X_col.T
        self._grad_weight = grad_weight.reshape(self._weight.shape)

        W_reshape = self._weight.reshape(n_filters, -1)
        dX_col = W_reshape.T @ output_grad_reshaped
        return col2im_indices(dX_col, self._X_shape, self._kernel_size, self._kernel_size, padding=self._padding, stride=self._stride)

class Linear(Module):
    def __init__(self,in_features, out_features):
        self._in_features = in_features
        self._out_features = out_features
        law_bound = 1/np.sqrt(in_features)
        self._bias = np.random.uniform(-law_bound,law_bound,size=(out_features)).astype(np.float32)
        self._weight = np.random.uniform(-law_bound,law_bound,size=(out_features, in_features)).astype(np.float32)

    def forward(self, X):
        self._last_input = X
        return np.matmul(X, self._weight.T) + np.tile(self._bias, (X.shape[0],1))

    def backward(self, output_grad):
        self._grad_bias = np.sum(output_grad,axis=0)
        self._grad_weight = np.dot(output_grad.T, self._last_input)
        return np.dot(output_grad, self._weight)
    
class Flatten(Module):
    def forward(self, X):
        self._X_shape = X.shape
        N = X.shape[0]
        return X.reshape(N, -1)

    def backward(self, output_grad):
        return output_grad.reshape(self._X_shape)

class Sequential(Module):
    def __init__(self, *modules):
        self._modules = list(modules)

    def add_module(self, module):
        self._modules.append(module)

    def forward(self, X):
        for module in self._modules:
            X = module.forward(X)
        return X

    def backward(self, output_grad):
        for module in reversed(self._modules):
            output_grad = module.backward(output_grad)
        return output_grad

    def step(self, optimizer):
        for module in self._modules:
            if isinstance(module, Linear) or isinstance(module, Conv2d):
                module.step(optimizer)

    def zero_grad(self):
        for module in self._modules:
            if isinstance(module, Linear) or isinstance(module, Conv2d):
                module.zero_grad()

    def parameters(self):
        parameters = []
        for module in self._modules:
            if isinstance(module, Linear) or isinstance(module, Conv2d):
                parameters.append(module._weight)
                parameters.append(module._bias)
        return parameters

class Variable(object):
    def __init__(self, data=None):
        self.data = data
        self.grad = None