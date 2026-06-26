from fastapi import FastAPI
import pandas as pd
from shap_explainer import explain_instance
from schemas import ExplainRequest, ExplainResponse
from schemas import (
    PredictionInput,
    PredictionHistoryItem,
    PredictionHistoryResponse
)
from model_loader import FEATURE_COLUMNS, imputer
from inference import ensemble_predict
from supabase_client import supabase  # (kept for history endpoint)

app = FastAPI(
    title="Clinical Decision Support System for CVD",
    description="Explainable, Uncertainty-Aware, Longitudinal CDSS",
    version="1.0"
)

# ---------------- HEALTH ----------------
@app.get("/")
def health_check():
    return {
        "status": "CVD CDSS API is running",
        "message": "Use POST /predict and GET /history/{op_number}"
    }

# ---------------- PREDICT ----------------
@app.post("/predict")
def predict(data: PredictionInput):

    try:
        input_dict = data.dict()
        op_number = input_dict.pop("op_number").strip()

        # Create DataFrame
        df = pd.DataFrame([input_dict])

        # Align columns with model
        df = df.reindex(columns=FEATURE_COLUMNS, fill_value=0)

        # Transform
        X = imputer.transform(df)

        # Predict
        risk_score, uncertainty, confidence, agreement = ensemble_predict(X)

        # ✅ RETURN ONLY (NO DB INSERT)
        return {
    "op_number": op_number,
    "risk_score": float(risk_score),
    "uncertainty": float(uncertainty),
    "confidence": str(confidence),
    "agreement": float(agreement)
}

    except Exception as e:
        return {"error": str(e)}

# ---------------- HISTORY ----------------
@app.get("/history/{op_number}", response_model=PredictionHistoryResponse)
def get_prediction_history(op_number: str):

    try:
        op_number = op_number.strip()

        response = (
            supabase
            .table("predictions")
            .select("risk_score, uncertainty, confidence, created_at")
            .eq("op_number", op_number)   # ⚠️ ensure this column exists if you use history
            .order("created_at", desc=False)
            .execute()
        )

        records = response.data or []

        history = [
            PredictionHistoryItem(
                risk_score=r["risk_score"],
                uncertainty=r["uncertainty"],
                confidence=r["confidence"],
                created_at=r["created_at"]
            )
            for r in records
        ]

        return {
            "op_number": op_number,
            "history": history
        }

    except Exception as e:
        return {"op_number": op_number, "history": []}

# ---------------- EXPLAIN ----------------
@app.post("/explain", response_model=ExplainResponse)
def explain(data: ExplainRequest):

    try:
        input_dict = data.dict()
        op_number = input_dict.pop("op_number").strip()

        df = pd.DataFrame([input_dict])
        df = df.reindex(columns=FEATURE_COLUMNS, fill_value=0)

        explanation = explain_instance(df)

        return {
            "op_number": op_number,
            "explanation": explanation
        }

    except Exception as e:
        return {"op_number": op_number, "explanation": {"error": str(e)}}