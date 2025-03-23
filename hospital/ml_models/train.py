import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report
import pickle


df2 = pd.read_csv("/Users/sameer/Desktop/BisonBytes/datasets/human_vital_signs_dataset_2024.csv")
# Convert Timestamp to datetime
df2['Timestamp'] = pd.to_datetime(df2['Timestamp'])

# Define features and target.
# We remove 'Patient ID' and 'Timestamp' as they are identifiers or not useful for prediction.
features = ['Heart Rate', 'Respiratory Rate', 'Body Temperature', 'Oxygen Saturation',
            'Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Age', 'Gender',
            'Weight (kg)', 'Height (m)']
target = 'Risk Category'

# First split: separate out the test set (20% of the data)
X_train_val, X_test, y_train_val, y_test = train_test_split(df2[features], df2[target],
                                                           test_size=0.2, random_state=42)

# Second split: split train+validation into training (60% overall) and validation (20% overall)
# Since X_train_val is 80% of the data, setting test_size=0.25 gives 0.25*80% = 20% for validation.
X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val,
                                                  test_size=0.25, random_state=42)

# Define which features are numeric and which are categorical.
numeric_features = ['Heart Rate', 'Respiratory Rate', 'Body Temperature', 'Oxygen Saturation',
                    'Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Age',
                    'Weight (kg)', 'Height (m)']
categorical_features = ['Gender']

# Create a preprocessor that scales numeric features and one-hot encodes categorical ones.
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(), categorical_features)
    ])

# Create a pipeline that first transforms the data then fits a Decision Tree classifier
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', DecisionTreeClassifier(random_state=42))
])

# Train the model on the training set
pipeline.fit(X_train, y_train)
# Evaluate the model on the validation set
y_val_pred = pipeline.predict(X_val)
print("Validation Set Performance:")
print(classification_report(y_val, y_val_pred))

# Evaluate the model on the test set
y_test_pred = pipeline.predict(X_test)
print("Test Set Performance:")
print(classification_report(y_test, y_test_pred))

# Optionally, save the trained pipeline as a pickle file
with open('/Users/sameer/Desktop/BisonBytes/hospital/ml_models/vitals-model.pkl', 'wb') as file:
    pickle.dump(pipeline, file)
