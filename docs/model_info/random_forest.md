# What is Linear Regression?
- Statistical technique used to find the relationship b/w variables
- In ML, linear regression finds relationship b/w features and a label

`y = b + w_1x_1`
y = predicted label (output)
b = bias (y-intercept)
w_1 = weight of feature (slope)
x_1 = feature (input)

Bias and weight are calculated from training

# Loss
- Loss is a numeric metric describing how wrong a model's predictions are
- L_1 Loss -> Sum of absolute values of the difference between the predicted values and actual values
- Mean Absolute Error -> Average of L_1 losses across a set of N examples
- L_2 Loss -> Sum of the squared difference between the predicted values and the actual values
- Mean Squared Error -> Average of L_2 losses across a set of N examples
- Root Mean Squared Error -> Square root of the mean squared error

- The MSE moves the model more towards the outliers, while MAE doesn't

# Gradient Descent
- Mathemetical technique which iteratively finds weights and bias which produce the model with lowest loss
- The model begins training with randomized weights and biases near zero, and repeats these steps
1. Calculate loss w/ current weight + bias
2. Determine direction to move the weights and bias to reduce loss
3. Move the weight and bias valeus a small amount in the direction that reduces loss
4. Return to step one and repeat the process until the model can't reduce the loss any further

# Hyperparameters
- Hyperparameters are variables which control different aspects of training; the three common being
1. Learning rate
2. Batch size
3. Epochs
- In contrast, parameters are like variables, like the weights and bias which are apart of the model itself, and hyperparameters are values that you can control

### Learning Rate
- Floating point number you set to influence how quickly the model converges
- If the learning rate is too low, the model can take a long time to converge
- If the learning rate is too high, the model never converges, but instead bounces around the weights and bias which minimize loss
- Determines the magnitude of the changes to make to the weights and bias during each step of the gradient descent process

### Batch Size
- Hyperparameter which refers to number of examples in the model processes before updating its weights and bias
- Two common techniques to get the right gradient on average without needing to look at every example before updating the weights and bias are stochastic gradient descent and mini-batch stochastic gradient descent

### Epochs
- During training, an epoch means that the model has processed every example in the training set once. 
- Training typically takes multiple epochs