# Phase 1: Predict how long a player will be out, for a given injury

## The Problem

Predict: total days a player will be out due to an injury (any)
Given: Injury type, body parts, player characteristics (input features)
Method: Random Forest Regressor

## Notebook Implementation (RandomForestRegressor_Phase1_MachineLearning.ipynb)

### Overview
This notebook creates a machine learning model via random forest regressor. This notebook loads NBA player injury data from (`BALL.db`), prepares the features to be used, and trains a basic random forest resgressot to predict how long a player will be out for an injury.


### Key Steps
1. **Database Connection**: Connects to `BALL.db` and lists available tables
2. **Data Loading**: Retrieves the `player_injury_profile` table from `BALL.db` into a Pandas dataframe, and inspects columns and shape
3. **Data Preparation**: 
   - Drops rows with missing target values (`total_days_out`), as these would negatively affect results of our model
   - Selects all numeric columns as features, excluding the target to allow the model to predict our label (days out to injury)
4. **Model Training & Evaluation**:
   - Splits data (80/20 train/test)
   - Builds a pipeline: median imputation for missing values + Random Forest (200 trees, in parallel)
   - Fits model, predicts on test set, evaluates with MAE, RMSE, and R²
5. **Results**:
   - Mean Absolute Error (MAE): 23.1 days
        - the average absolute distance between the model's predicted recovery days and the actual recovery days
            - not the most accurate, but reasonable for baseline model (we have to remember that injuries can vary widely)
   - Root Mean Squared Error (RMSE): 56.6 days
        - the square root of the average of the squared differences between predicted and actual values
            - model's errors are larger on average when squared. With the RMSE greater than the MAE, it shows that some predictions are signicicantly off
   - Coefficient of Determiniation (R²):  0.598
        - proportion of variance in target variable
            - model explains about 60% of the variation in recovery times; this means that it understands the factors which cause the recovery times to vary from player to player 60% of the time

### Conclusion

Phase 1 was able to establish a baseline machine learning model to predict NBA player injury recovery times using a Random Forest Regressor. By leveraging the `player_injury_profile` dataset from `BALL.db`, the model achieved moderate performance with an R² of 0.598, explaining about 60% of the variance in recovery durations. The MAE of 23.1 days indicates reasonable average accuracy for a phase 1 approach, but the higher RMSE (56.6 days) indicates challenges with outlier predictions for severe or prolonged injuries.

Reasons to why the model makes these errors could be because the model only sees basic player attributes and an overall injury count. It doesn't know about the type, and severity of the injurieswhich are important from distinguishing a sprain from a season-ending tear
The dataset is small and imbalances; there are many healthy players with zero days missed, and only a few players with very long absences, so the model doens't see enough of those examples with extreme patterns to learn them well

The model does perform decently for a "normal injury", but performs very poorly on severe injuries.

Next Steps can include:
- Add richer columns to add to the model
- Instead of predicting an exact day, we can instead predict a time frame
- Research better ways to optimize the model performance or swap to a different model (XGBoost potentially) 

