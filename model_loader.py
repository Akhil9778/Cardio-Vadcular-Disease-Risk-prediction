import joblib
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

lr_model = joblib.load(os.path.join(BASE_DIR, "logistic_regression.pkl"))
lgbm_model = joblib.load(os.path.join(BASE_DIR, "lightgbm.pkl"))
rf_model = joblib.load(os.path.join(BASE_DIR, "balanced_rf.pkl"))
imputer = joblib.load(os.path.join(BASE_DIR, "imputer.pkl"))

with open(os.path.join(BASE_DIR, "feature_columns.json"), "r") as f:
    FEATURE_COLUMNS = json.load(f)
