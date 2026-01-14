# XGBoost

## What are they?
- Extreme Gradient Boosting
- Scalable, distributed gradient-boosted decision tree machine learning library
- Allows trees to run in parallel and allows boosting
- Type of supervised machine learning model
- Type of ensemble learning algorithm (similar to random forest, for classification and regression)
    - Ensembly learning algorithms combine multiple ml algorithms to obtain a better model
- XGBoost models utilize bagging (common in random forest models); bagging is the ability to build full decision trees in parallel from random bootstrap samples of the dataset, and the final prediction is an average of all the decision tree predictions
- Bagging in XGBoost models minimize the bias and underfitting 
- Utilizes gradient boosting
    - Gradient boosting is an extention of boosting where the process of additvely generating weak models is formalized as a gradient descent algorithm over an objective function.

# Why XGBoost?
- Usage on a wide range of applications, including solving problems in regression, classification, ranking and user-defined prediction challenges
- Library is highly portable and runs on all desktop platforms
- Cloud integration w/ AWS, Azure and Yarn clusters
- XGBoost runs better with GPUs

# XGBoost vs Random Forest Trees
- Random Forest Trees build many decision trees independently using random samples and averages their predicitons; this reduces overfitting and improves accuracy by combining diverse models
- XGBoost builds trees sequentially, where each tree tries to correct the errors of the previous ones using gradient boosting. It optmizes the model by focusing on hard-to-predict cases and uses advanced techniques for speed and accuracy

# Use Cases
- Credit Scoring:
    - Banks and lenders utilize XGBoost to predict the likelihood that a customer will repay a loan. The model would analyze features like income, credit history, debt, and payment behaviour to assign a risk score. This helps to automate loan approvals as well as set interest rates
- Fraud Detection:
    - Financial institutions use XGBoost to spot suspicious transactions. The model learns from past examples of fraud and normal activity, and it uses specific features like transaction amount, location, time, and account history. It'll easily be able to detect unusual patterns that can indicate fraud, preventing losses

# Code Sample
```
# import required libraries

import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pandas as pd

# prepare data
df = pd.read_csv('ur_data.csv')
X = df.drop('target_column', axis=1)
y = df['target_column']

import numpy as np
# use random data (for demonstration)
X = np.random.rand(100, 5)
y = np.random.rand(100)

# split data into training and testing splits
X_train, X_test, y_train, y_test = train_test_split

# train XGBoost model
model = xgb.XGBRegressor()
model.fit(X_train, y_train)

# make predictions & evaluate performance
preds = model.predict(X_test)
rmse = mean_squared_error(y_test, preds, squared=False)
return rmse
```

# Hyperparameter Tuning
- Tuning hyperparameters helps you get the best performance from your model, and the common parameters to tune include:
    - learning_rate: how much each tree contributes (lower values -> improve accuracy but requires more trees)
    - max_depth: max depth of each tree (controls model complexity)
    - n_estimators: number of trees to build
    - subsample: fraction of samples used for each tree (prevents overfitting)
    - colsample_bytree: fraction of features used for each tree

# In Summary
XGBoost is a powerful, scalable machine learning library for building supervised models (regression, classification, ranking). It uses ensemble learning (combining multiple models) and uses advanced techniques like bagging or gradient boosting to improve accuracy and reduce bias. XGBoost is known to be fast, runs in parallel and works well on many platforms, and it used widely for a variety of prediction tasks

