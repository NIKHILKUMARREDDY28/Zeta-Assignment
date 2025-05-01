import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("💳 AI-Powered Customer Portal")

# --- 1. Show balance ---
st.header("1. Account Balance")
cust_id = st.text_input("Customer ID", value="cust_1")
if st.button("Fetch Balance"):
    res = requests.get(f"{API_URL}/balance", params={"customer_id": cust_id})
    if res.ok:
        data = res.json()
        st.success(f"Balance for {data['customer_id']}: ${data['balance']:.2f}")
    else:
        st.error(res.json().get("detail"))

st.markdown("---")


st.header("2. Apply for a Loan")
with st.form("loan_form"):
    credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=650)
    income = st.number_input("Monthly Income ($)", min_value=0.0, value=3000.0)
    open_loans = st.number_input("Number of Open Loans", min_value=0, value=0)
    submitted = st.form_submit_button("Check Eligibility")
    if submitted:
        payload = {
            "customer_id": cust_id,
            "credit_score": credit_score,
            "monthly_income": income,
            "open_loans": open_loans
        }
        res = requests.post(f"{API_URL}/loan-eligibility", json=payload)
        if res.ok:
            out = res.json()
            st.metric("Eligibility Score", out["eligibility_score"])
            st.info(out["recommendation"])
        else:
            st.error("Error checking eligibility")

st.markdown("---")

# --- 3. Dispute History ---
st.header("3. Dispute History")
if st.button("Load Disputes"):
    res = requests.get(f"{API_URL}/disputes", params={"customer_id": cust_id})
    if res.ok:
        disputes = res.json()
        if disputes:
            for d in disputes:
                st.write(f"• #{d['id']} — {d['issue']} (`{d['status']}`)")
        else:
            st.info("No disputes found.")
    else:
        st.error("Error fetching disputes")

st.subheader("File a New Dispute")
new_issue = st.text_input("Issue Description")
if st.button("Submit Dispute"):
    res = requests.post(f"{API_URL}/disputes", json={
        "customer_id": cust_id,
        "issue": new_issue
    })
    if res.ok:
        st.success("Dispute filed!")
    else:
        st.error("Failed to file dispute")
