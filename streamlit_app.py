import streamlit as st
from database import supabase
import requests
from datetime import datetime
import plotly.express as px
import pandas as pd

BACKEND_URL = "https://umeshkrishnaa-cvd-cdss-api.hf.space/predict"

st.set_page_config(page_title="CVD Longitudinal CDSS", layout="wide")

# ================= SESSION INIT =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"

# ================= CLINICAL RULES =================
def clinical_rules(age, sbp, dbp, glucose, ldl, cad, diabetes, hypertension):

    factors = []
    alerts = []

    if age >= 60:
        factors.append("Age ≥ 60")

    if sbp > 160:
        factors.append("Very high systolic BP")
        alerts.append("⚠️ Poor blood pressure control — optimize antihypertensive therapy.")

    if dbp > 95:
        factors.append("Very high diastolic BP")

    if glucose > 180:
        factors.append("Severely elevated glucose")
        alerts.append("⚠️ Severe hyperglycemia — review glycemic control.")

    if ldl > 160:
        factors.append("Very high LDL cholesterol")
        alerts.append("⚠️ Very high LDL — consider statin intensification.")

    if cad == 1:
        factors.append("Existing coronary artery disease")
        alerts.append("⚠️ Known CAD — cardiology follow-up advised.")

    if diabetes == 1:
        factors.append("Diabetes mellitus")
        alerts.append("⚠️ Diabetes present — regular monitoring required.")

    if hypertension == 1:
        factors.append("Hypertension")

    if len(factors) >= 4:
        flag = "HIGH CLINICAL RISK"
    elif len(factors) >= 1:
        flag = "MODERATE CLINICAL RISK"
    else:
        flag = "LOW CLINICAL RISK"

    return flag, factors, alerts

# ================= LOGIN =================
def login_page():
    st.title("🏥 Cardiovascular CDSS")

    doctor_id = st.text_input("Doctor ID")

    if st.button("Login"):
        try:
            response = supabase.table("doctors").select("*").eq("doctor_id", doctor_id).execute()
            if response.data:
                st.session_state.logged_in = True
                st.session_state.doctor = response.data[0]
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid Doctor ID")
        except Exception as e:
            st.error(f"Login Error: {e}")

# ================= DASHBOARD =================
def dashboard_page():
    st.title("📊 Dashboard")
    st.write(f"Welcome, **Dr. {st.session_state.doctor['name']}**")

    if st.button("Patient Register / Search"):
        st.session_state.page = "patient_register"
        st.rerun()

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.page = "login"
        st.rerun()

# ================= PATIENT REGISTER =================
def patient_register_page():
    st.title("🧾 Patient Register / Search")

    tab1, tab2 = st.tabs(["Search", "Register"])

    with tab1:
        op = st.text_input("Enter OP Number")
        if st.button("Search"):
            res = supabase.table("patients").select("*").eq("op_number", op).execute()
            if res.data:
                st.session_state.patient = res.data[0]
                st.session_state.page = "patient_history"
                st.rerun()
            else:
                st.warning("Patient not found")

    with tab2:
        new_op = st.text_input("OP Number")
        name = st.text_input("Name")
        age = st.number_input("Age", min_value=0)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        if st.button("Register"):
            if not new_op or not name:
                st.warning("Fill all fields")
                return

            supabase.table("patients").insert({
                "op_number": new_op,
                "name": name,
                "age": age,
                "gender": gender
            }).execute()

            st.success("Patient Registered")

# ================= PATIENT HISTORY =================
def patient_history_page():
    patient = st.session_state.patient
    st.title(f"📁 {patient['name']} (OP: {patient['op_number']})")

    # 👇 REPLACED BLOCK HERE
    visits = supabase.table("visits").select("*").execute()

    filtered_visits = [
        v for v in visits.data
        if v.get("patient_id") == patient["id"]
    ]

    if filtered_visits:
        for v in filtered_visits:
            if st.button(f"View {v['visit_date']}", key=v["id"]):
                st.session_state.visit_id = v["id"]
                st.session_state.page = "visit_report"
                st.rerun()
    else:
        st.info("No visits found")

    # 👇 KEEP THIS
    if st.button("➕ Add Visit"):
        st.session_state.page = "add_visit"
        st.rerun()

# ================= ADD VISIT =================
def add_visit_page():

    patient = st.session_state.patient
    st.title(f"➕ Add Visit for {patient['name']}")

    age = st.number_input("Age")
    sbp = st.number_input("Systolic BP")
    dbp = st.number_input("Diastolic BP")
    glucose = st.number_input("Glucose")
    total_chol = st.number_input("Total Cholesterol")
    hdl = st.number_input("HDL")
    ldl = st.number_input("LDL")

    hypertension = st.selectbox("Hypertension", [0,1])
    diabetes = st.selectbox("Diabetes", [0,1])
    cad = st.selectbox("CAD", [0,1])

    if st.button("Save & Predict"):

        payload = {
            "op_number": patient["op_number"],
            "age_at_visit": age,
            "Systolic_Blood_Pressure": sbp,
            "Diastolic_Blood_Pressure": dbp,
            "Glucose": glucose,
            "Total_Cholesterol": total_chol,
            "High_Density_Lipoprotein_Cholesterol": hdl,
            "Low_Density_Lipoprotein_Cholesterol": ldl,
            "hypertension": hypertension,
            "diabetes": diabetes,
            "hyperlipidemia": 0,
            "cad": cad,
            "stroke": 0,
            "comorbidity_count": 0,
            "bp_med": 0,
            "diabetes_med": 0,
            "statin": 0,
            "treatment_duration_days": 0
        }

        response = requests.post(BACKEND_URL, json=payload, timeout=10)

        result = response.json()

        if "error" in result:
            st.error(result["error"])
            return

        visit = supabase.table("visits").insert({
            "patient_id": patient["id"],
            "doctor_id": st.session_state.doctor["id"],
            "visit_date": datetime.now().isoformat(),
            "age_at_visit": age,
            "systolic_bp": sbp,
            "diastolic_bp": dbp,
            "glucose": glucose,
            "total_cholesterol": total_chol,
            "hdl": hdl,
            "ldl": ldl,
            "cad": cad,
            "diabetes": diabetes,
            "hypertension": hypertension
        }).execute()

        visit_id = visit.data[0]["id"]

        supabase.table("predictions").insert({
    "visit_id": visit_id,
    "ml_risk_score": result["risk_score"],
    "confidence": result["uncertainty"],
    "combined_risk": result["confidence"],
    "agreement": result.get("agreement", 0)
}).execute()

        st.session_state.visit_id = visit_id
        st.session_state.page = "visit_report"
        st.rerun()

# ================= VISIT REPORT =================
def visit_report_page():

    visit_id = st.session_state.get("visit_id")

    if not visit_id:
        st.error("Visit not found")
        return

    # ---------------- FETCH DATA ----------------
    visit_res = supabase.table("visits").select("*").eq("id", visit_id).execute()
    pred_res = supabase.table("predictions").select("*").eq("visit_id", visit_id).execute()

    if not visit_res.data or not pred_res.data:
        st.error("Data not found")
        return

    visit = visit_res.data[0]
    pred = pred_res.data[0]

    # ---------------- EXTRACT VALUES ----------------
    risk_score = float(pred.get("ml_risk_score", 0))
    uncertainty = float(pred.get("confidence", 0))
    risk_category = pred.get("combined_risk", "UNKNOWN")
    agreement = float(pred.get("agreement") or 0)

    # ================= TOP HEADER =================
    st.markdown(f"## 🧠 {risk_category.upper()} ML RISK")

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", round(risk_score, 3))
    col2.metric("Model Confidence", risk_category)
    col3.metric("Uncertainty", round(uncertainty, 3))

    st.divider()

    # ================= CONFIDENCE EXPLANATION =================
    st.info(
        f"Confidence Explanation: {risk_category} confidence due to "
        f"{'low uncertainty' if uncertainty < 0.08 else 'higher uncertainty'} "
        f"and model agreement score of {round(agreement, 3)}."
    )

    # Agreement bar
    st.progress(min(max(agreement, 0), 1))
    st.caption("Model Agreement Score")

    st.divider()

    # ================= CLINICAL RULES =================
    flag, factors, alerts = clinical_rules(
        visit["age_at_visit"],
        visit["systolic_bp"],
        visit["diastolic_bp"],
        visit["glucose"],
        visit["ldl"],
        visit.get("cad", 0),
        visit.get("diabetes", 0),
        visit.get("hypertension", 0)
    )

    st.markdown("### 🩺 Clinical Risk Flag (Rule-Based)")

    if flag == "HIGH CLINICAL RISK":
        st.error(f"🔴 {flag}")
    elif flag == "MODERATE CLINICAL RISK":
        st.warning(f"🟠 {flag}")
    else:
        st.success(f"🟢 {flag}")

    # ================= FACTORS =================
    if factors:
        st.markdown("**Risk factors triggering this flag:**")
        for f in factors:
            st.write(f"- {f}")

    st.divider()

    # ================= CLINICAL SUMMARY =================
    st.markdown("### 🧾 Clinical Summary")

    summary = f"The patient demonstrates {flag.lower()} baseline clinical risk. "
    summary += f"The ML model estimates {risk_category.lower()} short-term cardiovascular event risk. "

    if factors:
        summary += "Key contributing clinical factors include: " + ", ".join(factors) + ". "

    summary += "This output supports clinical decision-making."

    st.write(summary)

    # ================= ALERTS =================
    if alerts:
        st.divider()
        st.markdown("### ⚠️ Alerts & Recommendations")
        for alert in alerts:
            st.warning(alert)

    st.divider()

    # ================= DOCTOR NOTES =================
    st.markdown("### 📝 Doctor Observation")

    observation = st.text_area(
        "Enter or update doctor observation:",
        value=visit.get("doctor_observation", ""),
        height=150
    )

    if st.button("Save Observation"):
        supabase.table("visits").update({
            "doctor_observation": observation
        }).eq("id", visit_id).execute()

        st.success("Observation saved successfully.")

    st.divider()

    # ================= LONGITUDINAL ANALYSIS =================
    st.markdown("## 📊 Longitudinal Analysis")

    all_visits = supabase.table("visits") \
        .select("*") \
        .eq("patient_id", visit["patient_id"]) \
        .order("visit_date") \
        .execute()

    trend_data = []
    vitals_data = []

    for v in all_visits.data:
        p = supabase.table("predictions") \
            .select("*") \
            .eq("visit_id", v["id"]) \
            .execute()

        if p.data:
            trend_data.append({
                "Visit Date": v["visit_date"],
                "Risk Score": p.data[0]["ml_risk_score"]
            })

        vitals_data.append({
            "Visit Date": v["visit_date"],
            "Systolic BP": v["systolic_bp"],
            "Diastolic BP": v["diastolic_bp"],
            "Glucose": v["glucose"],
            "LDL": v["ldl"]
        })

    # ---- Risk Trend ----
    if trend_data:
        df = pd.DataFrame(trend_data)
        st.plotly_chart(
            px.line(df, x="Visit Date", y="Risk Score", markers=True),
            use_container_width=True
        )

    # ---- Vitals Graphs ----
    if vitals_data:
        df_vitals = pd.DataFrame(vitals_data)

        st.plotly_chart(
            px.line(df_vitals, x="Visit Date", y=["Systolic BP", "Diastolic BP"], markers=True),
            use_container_width=True
        )

        st.plotly_chart(
            px.line(df_vitals, x="Visit Date", y="Glucose", markers=True),
            use_container_width=True
        )

        st.plotly_chart(
            px.line(df_vitals, x="Visit Date", y="LDL", markers=True),
            use_container_width=True
        )

    # ================= BACK =================
    if st.button("⬅ Back"):
        st.session_state.page = "patient_history"
        st.rerun()
# ================= ROUTING =================
if not st.session_state.logged_in:
    login_page()
elif st.session_state.page == "dashboard":
    dashboard_page()
elif st.session_state.page == "patient_register":
    patient_register_page()
elif st.session_state.page == "patient_history":
    patient_history_page()
elif st.session_state.page == "add_visit":
    add_visit_page()
elif st.session_state.page == "visit_report":
    visit_report_page()