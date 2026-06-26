import numpy as np
from model_loader import lgbm_model, rf_model, lr_model

def ensemble_predict(X):

    # ---------------- INDIVIDUAL MODEL PREDICTIONS ----------------
    pred_lgbm = lgbm_model.predict_proba(X)[0][1]
    pred_rf = rf_model.predict_proba(X)[0][1]
    pred_lr = lr_model.predict_proba(X)[0][1]

    # ---------------- ENSEMBLE AVERAGE ----------------
    risk_score = (pred_lgbm + pred_rf + pred_lr) / 3

    # ---------------- UNCERTAINTY ----------------
    preds = np.array([pred_lgbm, pred_rf, pred_lr])
    uncertainty = np.var(preds)

    # ---------------- AGREEMENT ----------------
    agreement = 1 - np.std(preds)

    # ---------------- CONFIDENCE LOGIC ----------------
    if uncertainty < 0.02 and agreement > 0.9:
        confidence = "HIGH"
    elif uncertainty < 0.08:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return risk_score, uncertainty, confidence, agreement