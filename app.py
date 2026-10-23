import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_drawable_canvas import st_canvas

# Force wide-screen professional dashboard viewport
st.set_page_config(page_title="Advance America | E-Sign Portal", layout="wide")

# Injection of custom CSS styling rules to align branding perfectly
st.markdown("""
    <style>
        .main-header { font-size: 28px; font-weight: 900; color: #0F172A; text-transform: uppercase; letter-spacing: -0.5px; display: flex; align-items: center; }
        .accent-text { color: #F59E0B; margin-left: 6px; }
        .tila-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 16px; border-radius: 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .tila-title { font-size: 10px; font-weight: 700; color: #64748B; text-transform: uppercase; tracking-wider; margin-bottom: 4px; }
        .tila-val { font-size: 22px; font-weight: 900; color: #0F172A; }
        .disclosure-notice { background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 8px; font-size: 13px; color: #78350F; line-height: 1.5; text-align: justify; }
        .contract-title { font-size: 20px; font-weight: 900; color: #0F172A; text-transform: uppercase; text-align: center; tracking-wide; }
        .contract-subtitle { font-size: 11px; color: #94A3B8; text-transform: uppercase; text-align: center; letter-spacing: 1px; margin-top: -8px; margin-bottom: 20px; }
        .print-btn {
            display: block; width: 100%; background-color: #F59E0B; color: #0F172A !important; 
            font-weight: 900; text-align: center; padding: 12px; border-radius: 12px; 
            text-decoration: none; border: none; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .print-btn:hover { background-color: #D97706; }
        @media print {
            header, [data-testid="stSidebar"], .no-print, [data-testid="stForm"] { display: none !important; }
            div[data-testid="stColumn"] { width: 100% !important; flex: 1 1 auto !important; }
        }
    </style>
""", unsafe_allow_html=True)

# Newton-Raphson calculation engine for exact APR
def calculate_apr(principal, fee, emi, tenure):
    net_received = principal - fee
    if net_received <= 0 or emi <= 0:
        return 0.0
    r = 0.01 
    for _ in range(100):
        f = sum(emi / ((1 + r) ** m) for m in range(1, tenure + 1)) - net_received
        df = sum(-(m * emi) / ((1 + r) ** (m + 1)) for m in range(1, tenure + 1))
        if df == 0: break
        r_next = r - f / df
        if abs(r_next - r) < 1e-6:
            r = r_next
            break
        r = r_next
    return r * 12 * 100

# Top Branding Panel Alignment Block
col_logo, col_trust = st.columns(2)
with col_logo:
    st.markdown('<div class="main-header">🔹 Advance <span class="accent-text">America</span></div>', unsafe_allow_html=True)
with col_trust:
    st.markdown("<div style='text-align: right; font-size: 11px; font-weight: bold; color: #94A3B8; margin-top:14px; letter-spacing: 0.5px;'>🛡️ FDIC INSURED • BBB A+ COMPLIANT</div>", unsafe_allow_html=True)

st.divider()

# Setup URL parsing tracking logic rules
query_params = st.query_params
is_borrower_view = "view" in query_params and query_params["view"] == "borrower"

# ----------------------------------------------------
# 🏢 INTERFACE MODE A: LENDER ADMIN CONSOLE
# ----------------------------------------------------
if not is_borrower_view:
    st.subheader("📋 Loan Agreement Parameters Configuration Dashboard")
    st.caption("Enter borrower underwriting metrics below to compile a legal digital signing portal link.")

    with st.form("lender_generation_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Borrower Full Name", value="John Doe")
            email = st.text_input("Borrower Email Address", value="john.doe@example.com")
            bank = st.text_input("Disbursement Bank Account Info", value="Chase Bank (Acc: *******5678)")
        with col2:
            address = st.text_input("Physical Residential Address", value="123 Financial Way, San Francisco, CA")
            amount = st.number_input("Principal Loan Amount ($)", min_value=1000, max_value=250000, value=10000, step=1000)
            tenure = st.slider("Amortization Tenure Duration (Months)", min_value=12, max_value=60, value=24)
            
        first_payment_date = st.date_input("First Installment Payment Milestone Due Date", datetime.today() + relativedelta(months=1))
        submit_btn = st.form_submit_button("Generate Secure Borrower Signature URL Link")

    if submit_btn:
        encoded_link = (
            f"https://streamlit.app"
            f"&n={name.replace(' ', '+')}"
            f"&a={address.replace(' ', '+')}"
            f"&b={bank.replace(' ', '+')}"
            f"&p={amount}"
            f"&t={tenure}"
            f"&d={first_payment_date.strftime('%Y-%m-%d')}"
        )
        
        st.success("🚀 Secure E-Sign Link Formed Successfully!")
        st.info("Copy the generated link below and forward it directly to your customer:")
        st.code(encoded_link, language="text")

# ----------------------------------------------------
# 🖋️ INTERFACE MODE B: BORROWER SECURE E-SIGN PORTAL
# ----------------------------------------------------
else:
    p_name = query_params.get("n", "John Doe").replace("+", " ")
    p_addr = query_params.get("a", "123 Financial Way, San Francisco, CA").replace("+", " ")
    p_bank = query_params.get("b", "First National Bank (Acc: *******4321)").replace("+", " ")
    p_principal = float(query_params.get("p", 10000))
    p_tenure = int(query_params.get("t", 24))
    p_date_str = query_params.get("d", datetime.today().strftime("%Y-%m-%d"))

    # Execute math equations server-side
    fee = p_principal * 0.025
    total_interest = p_principal * 0.08 * (p_tenure / 12)
    total_repayment = p_principal + total_interest
    emi = total_repayment / p_tenure
    apr = calculate_apr(p_principal, fee, emi, p_tenure)
    start_date = datetime.strptime(p_date_str, "%Y-%m-%d")

    doc_col, action_col = st.columns([7, 5], gap="large")

    with doc_col:
        st.markdown('<div class="contract-title">Promissory Note & Secured Loan Agreement</div>', unsafe_allow_html=True)
        st.markdown('<div class="contract-subtitle">Executed under federal truth-in-lending parameters (TILA disclosures)</div>', unsafe_allow_html=True)

        t1, t2, t3, t4 = st.columns(4)
        with t1: st.markdown(f'<div class="tila-box"><div class="tila-title">GROSS PRINCIPAL</div><div class="tila-val">${p_principal:,.2f}</div></div>', unsafe_allow_html=True)
        with t2: st.markdown(f'<div class="tila-box"><div class="tila-title">ANNUAL PERCENTAGE (APR)</div><div class="tila-val" style="color:#D97706;">{apr:.2f}%</div></div>', unsafe_allow_html=True)
        with t3: st.markdown(f'<div class="tila-box"><div class="tila-title">MONTHLY PAYMENT (EMI)</div><div class="tila-val" style="color:#2563EB;">${emi:,.2f}</div></div>', unsafe_allow_html=True)
        with t4: st.markdown(f'<div class="tila-box"><div class="tila-title">TOTAL REPAYMENT COST</div><div class="tila-val">${total_repayment:,.2f}</div></div>', unsafe_allow_html=True)

        st.write("")
        
        st.markdown(f"""
        This Agreement is entered into and executed on this current calendar timeline milestone date, by and between the creditor, 
        **Advance America Financial Outlets**, and the underwritten borrower, **{p_name}**, residing at address locations **{p_addr}**.
        
        ###### 1. Amount Financed & Administrative Capitalized Processing Premiums
        The core principal balance advanced under this framework is **${p_principal:,.2f}**. The Borrower acknowledges that an integrated 
        fixed **2.50% processing fee** amounting to **${fee:,.2f}** has been capitalized and included within the structured financing note frame. 
        Account disbursements are directly synchronized with the verified clearing account at **{p_bank}**.
        
        ###### 2. Interest Rate Calculations & Amortization Payment Tracks
        Interest on this note is calculated using a **8.00% Flat Interest Rate per annum**. The total interest calculated over the dynamic 
        tenure of **{p_tenure} months** amounts to **${total_interest:,.2f}**. Consequently, the regular scheduled monthly installment payment 
        is established at **${emi:,.2f}** per month, commencing on the first installment milestone due date of **{start_date.strftime('%B %d, %Y')}**.
        """)

        st.markdown(f"""
        <div class="disclosure-notice">
            ⚠️ <strong>IMPORTANT DISCLOSURE ON CREDIT EVALUATION & CAPACITY:</strong> Advance America utilizes credit underwriting 
            frameworks to monitor risk allowances. Final approval parameters remain contingent on continuous real-time analysis of the 
            borrower's recurring debt-to-income capabilities. Defaulters will face immediate negative credit bureau reporting markers.
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        st.markdown("###### 3. Month-By-Month Customized Financial Amortization Schedule")

        schedule_rows = []
        running_bal = total_repayment
        p_step = p_principal / p_tenure
        i_step = total_interest / p_tenure
        curr_due_date = start_date

        for m_idx in range(1, p_tenure + 1):
            running_bal -= emi
            if running_bal < 0.01: running_bal = 0
            schedule_rows.append({
                "Inst. #": m_idx,
                "Due Date Milestone": curr_due_date.strftime("%b %d, %Y"),
                "Installment (EMI)": f"${emi:.2f}",
                "Principal Portion": f"${p_step:.2f}",
