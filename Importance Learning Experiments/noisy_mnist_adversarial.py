# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 21:26:21 2018

@author: Akshay
"""

## test_cw_mnist.py
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import sys
#sys.path.append('/home/hammj/Dropbox/Research/AdversarialLearning/codes/lib/cleverhans-master')

import numpy as np
from six.moves import xrange
import tensorflow as tf
from tensorflow.python.platform import flags

import logging
import os
from cleverhans.utils import pair_visual, grid_visual, AccuracyReport
from cleverhans.utils import set_log_level
from cleverhans.utils_mnist import data_mnist
from cleverhans.utils_tf import model_train, model_eval, tf_model_load, batch_eval, model_argmax
from cleverhans_tutorials.tutorial_models import make_basic_cnn
from bilevel_mt_new import bilevel_mt
import time
from cleverhans.utils_tf import model_loss

# MNIST-specific dimensions
img_rows = 28
img_cols = 28
channels = 1

# Get MNIST data
X_train_all, Y_train_all, X_test_all, Y_test_all = data_mnist(train_start=0, train_end=60000, test_start=0, test_end=10000)


X_all = X_train_all[:60000]
Y_all = Y_train_all[:60000]

tr = 59000
X_train = X_all[:tr]
Y_train = Y_all[:tr]
X_val = X_all[tr:60000]
Y_val = Y_all[tr:60000]
X_test = X_test_all
Y_test = Y_test_all

print(Y_train[0])
corrupt = 14750#14750#29750#44250
for i in range(corrupt):
    j = np.where(Y_train[i] == 1)[0]
    #print(j)
    j = (j+1)%10
    Y_train[i] = np.zeros(10)
    Y_train[i][j] = 1
    #print(np.where(Y_train[i] == 1)[0])
    
# Object used to keep track of (and return) key accuracies
report = AccuracyReport()
# Set TF random seed to improve reproducibility
tf.set_random_seed(1234)

# Create TF session
sess = tf.Session()
print("Created TensorFlow session.")

set_log_level(logging.DEBUG)
# Define input TF placeholder
x_tf = tf.placeholder(tf.float32, shape=(None, img_rows, img_cols, channels))
y_tf = tf.placeholder(tf.float32, shape=(None, 10))

# Define TF model graph
scope_model = 'mnist_classifier'
with tf.variable_scope(scope_model):    
    model = make_basic_cnn()
preds = model(x_tf)
    
var_model = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,scope=scope_model)        
saver_model = tf.train.Saver(var_model,max_to_keep=None)
print("Defined TensorFlow model graph.")

###########################################################################
# Training the model using TensorFlow
###########################################################################

# Train an MNIST model
train_params = {
    'nb_epochs': 100,
    'batch_size': 128,
    'learning_rate': 1E-3,
    'train_dir': os.path.join(*os.path.split(os.path.join("models", "mnist"))[:-1]),
    'filename': os.path.split( os.path.join("models", "mnist"))[-1]
}

rng = np.random.RandomState([2017, 8, 30])

######## ORACLE ########## 0.9785
if False:
    X = X_all[corrupt:60000]
    Y = Y_all[corrupt:60000]
    model_train(sess, x_tf, y_tf, preds, X, Y, args=train_params, save=os.path.exists("models"), rng=rng)
    
    # Evaluate the accuracy of the MNIST model on legitimate test examples
    eval_params = {'batch_size': 128}
    accuracy = model_eval(sess, x_tf, y_tf, preds, X_test, Y_test, args=eval_params)
    #assert X_test.shape[0] == 10000 - 0, X_test.shape
    print('Test accuracy of the ORACLE: {0}'.format(accuracy))
    report.clean_train_clean_eval = accuracy
    
######## Baseline ########## 0.8627
if False:
    X = np.concatenate((X_train, X_val), axis = 0)
    print(len(X))
    Y = np.concatenate((Y_train, Y_val), axis = 0)
    print(len(Y))
    model_train(sess, x_tf, y_tf, preds, X, Y, args=train_params, save=os.path.exists("models"), rng=rng)
    
    # Evaluate the accuracy of the MNIST model on legitimate test examples
    eval_params = {'batch_size': 128}
    accuracy = model_eval(sess, x_tf, y_tf, preds, X_test, Y_test, args=eval_params)
    assert X_test.shape[0] == 10000 - 0, X_test.shape
    print('Test accuracy of the ORACLE: {0}'.format(accuracy))
    report.clean_train_clean_eval = accuracy
    
######## Bilevel ########## 0.8627
if True:
    
    X = X_val
    Y = Y_val
    model_train(sess, x_tf, y_tf, preds, X, Y, args=train_params, save=os.path.exists("models"), rng=rng)
    
    # Evaluate the accuracy of the MNIST model on legitimate test examples
    eval_params = {'batch_size': 128}
    accuracy = model_eval(sess, x_tf, y_tf, preds, X_test, Y_test, args=eval_params)
    #assert X_test.shape[0] == 10000 - 0, X_test.shape
    print('Test accuracy of the ORACLE: {0}'.format(accuracy))
    accuracy = model_eval(sess, x_tf, y_tf, preds, X_train, Y_train, args=eval_params)
    #assert X_test.shape[0] == 10000 - 0, X_test.shape
    print('Train accuracy of the ORACLE: {0}'.format(accuracy))
    report.clean_train_clean_eval = accuracy
    
    #Y_train_init = model_argmax(sess, x_tf, preds, X_train)
    feed_dict = {x_tf: X_train}
    Y_train_init = sess.run(preds, feed_dict)
    
    importance_atan = np.ones((X_train.shape[0]))
    
    
    c = 0
    d = 0
    for i in range(Y_train.shape[0]):
        a = np.argwhere(Y_train[i] == 1)
        b = np.argmax(Y_train_init[i])
        e = np.max(Y_train_init[i])
        #print(b)
        if a == b and e > 0.6:
            c += 1
            importance_atan[i] = np.arctanh(0.9)
        elif a == b:
            c += 1
            importance_atan[i] = np.arctanh(0.5)
        else:
            d += 1
            importance_atan[i] = np.arctanh(0.1)
                          
    print(c)
    print(d)
    print(len(np.where(importance_atan > 0.5)[0]))
    print(len(np.where(importance_atan < 0.5)[0]))
    lr_outer = 1#0.5#1
    lr_inner = 6*1E-5#1E-4#6*1E-5#1E-5
    rho = 0 # 1E1 for non L1 radius
    sig = lr_inner
    batch_size = 128
    nepochs = 25#100#40#25
    height = 28
    width = 28
    nch = 1
    nb_classes = 10
    blmt = bilevel_mt(sess, model, var_model, batch_size, lr_outer, lr_inner, height, width, nch, nb_classes, rho, sig)
    #importance_atan = np.ones((X_train.shape[0]))    
    #sess.run(tf.global_variables_initializer())
    
    for epoch in range(nepochs):
        tick = time.time()        
        #nb_batches = int(np.ceil(float(Ntrain) / FLAGS.batch_size))
        nb_batches = int(np.floor(float(X_train.shape[0]) / batch_size))
        index_shuf = np.arange(X_train.shape[0])
        np.random.shuffle(index_shuf)
        
        for batch in range(nb_batches):
            ind = range(batch_size*batch, min(batch_size*(1+batch), X_train.shape[0]))
            #if len(ind)<FLAGS.batch_size:
            #    ind.extend([np.random.choice(Ntrain,FLAGS.batch_size-len(ind))])
            ind_val = np.random.choice(X_val.shape[0], size=(batch_size), replace=False)
            lin,lout1,lout2,lout3,timp_atan = blmt.train(X_train[index_shuf[ind],:], Y_train[index_shuf[ind],:], X_val[ind_val,:], Y_val[ind_val,:], importance_atan[index_shuf[ind]])
            importance_atan[index_shuf[ind]] = timp_atan

        ## Should I renormalize importance_atan?
        if True:
            importance = 0.5 * (np.tanh(importance_atan)+1.) # scale to beteen [0 1] from [-1 1]
            importance = 0.5 * X_train.shape[0] * importance / sum(importance)
            importance = np.maximum(.00001, np.minimum(.99999, importance))
            importance_atan = np.arctanh(0.99999 * (2. * importance - 1.))
            
        
        if epoch %1 == 0:
            print('epoch %d: loss_inner=%f, loss_inner2=%f, loss_outer1=%f, loss_outer3=%f'%(epoch,lin,lout1,lout2,lout3))
            print('mean ai=%f, mean I(ai>0.1)=%f'%(np.mean(importance),len(np.where(importance>0.1)[0])/np.float(X_train.shape[0])))
            print(np.mean(importance[corrupt:]))
            print(np.mean(importance[:corrupt]))
            
        if epoch % 1 == 0:
            print('acc = %f'%(model_eval(sess, x_tf, y_tf, preds, X_val, Y_val, args={'batch_size':batch_size})))
            #print('tr acc = %f'%(model_eval(sess, x_tf, y_tf, preds, X_train, Y_train, args={'batch_size':batch_size})))
            #print('epoch %d: loss_inner=%f, loss_outer1=%f, loss_outer2=%f'%(epoch,lin,lout1,lout2))   
                
    saver_model.save(sess,'./model_bilevel_mt_mnist.ckpt')
    #importance = 0.5*(np.tanh(importance_atan)+1.)
    np.save('./importance.npy',importance)
    
    ## Now, retrain temp model with the reduced set and evaluate accuracy
    model_path = os.path.join('models', 'temp_mnist')
    train_params = {'nb_epochs':100, 'batch_size':128, 'learning_rate':1E-3, 
        'train_dir': os.path.join(*os.path.split(model_path)[:-1]),
        'filename': os.path.split(model_path)[-1]
    }
    for pct in [0, 1, 2, 3, 4, 5]: # percentile from top
        #noise = 1E-6*np.random.normal(size=importance.shape)
        #th = np.percentile(importance + noise,100.-pct) # percentile from bottom
        #ind = pct * X_train.shape[0] #np.where(importance + noise >=th)[0]
        ## Make sure the training starts with random initialization
        if pct != 0:
            ind = np.argsort(importance)[-pct * 500 :]
            #print(np.maximum(importance), np.minimum(importance))
            X = np.concatenate((X_train[ind,:], X_val), axis = 0)
            print(len(X))
            print(len(np.where(ind > corrupt)[0]))
            Y = np.concatenate((Y_train[ind,:], Y_val), axis = 0)
            print(len(Y)) 
        else:
            ind = []
            #print(np.maximum(importance), np.minimum(importance))
            X = X_val
            print(len(X))
            Y = Y_val
            print(len(Y)) 
        #sess.run(tf.global_variables_initializer())
        model_train(sess, x_tf, y_tf, preds, X, Y,args=train_params)
        
        print('Bilevel acc (pct=%f,N=%d) = %f'%(pct,len(ind),model_eval(sess, x_tf, y_tf, preds, X_test, Y_test, args={'batch_size':batch_size})))


######## Random ########## 0.8627
if False:
    ## Now, retrain temp model with the reduced set and evaluate accuracy
    model_path = os.path.join('models', 'temp_mnist')
    train_params = {'nb_epochs':100, 'batch_size':128, 'learning_rate':1E-3, 
        'train_dir': os.path.join(*os.path.split(model_path)[:-1]),
        'filename': os.path.split(model_path)[-1]
    }
    importance = np.arange(0, X_train.shape[0])
    np.random.shuffle(importance)
    for pct in [0, 1, 2, 3, 4, 5]: # percentile from top
        #noise = 1E-6*np.random.normal(size=importance.shape)
        #th = np.percentile(importance + noise,100.-pct) # percentile from bottom
        #ind = pct * X_train.shape[0] #np.where(importance + noise >=th)[0]
        ## Make sure the training starts with random initialization
        if pct != 0:
            ind = np.argsort(importance)[-pct * 500 :]
            #print(np.maximum(importance), np.minimum(importance))
            X = np.concatenate((X_train[ind,:], X_val), axis = 0)
            print(len(np.where(ind > corrupt)[0]))
            print(len(X))
            Y = np.concatenate((Y_train[ind,:], Y_val), axis = 0)
            print(len(Y)) 
        else:
            ind = []
            #print(np.maximum(importance), np.minimum(importance))
            X = X_val
            print(len(X))
            Y = Y_val
            print(len(Y))
        
        model_train(sess, x_tf, y_tf, preds, X, Y,args=train_params)
        
        print('Random acc (pct=%f,N=%d) = %f'%(pct,len(ind),model_eval(sess, x_tf, y_tf, preds, X_test, Y_test, args={'batch_size':128})))