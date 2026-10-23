import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from streamlit_drawable_canvas import st_canvas

# Page Layout Parameters setup
st.set_page_config(page_title="Advance America | E-Sign Portal", layout="wide")

# Custom UI Branding Color Theme Injector Layer
st.markdown("""
    <style>
        .main-header { font-size: 26px; font-weight: 900; color: #0F172A; text-transform: uppercase; letter-spacing: -0.5px; }
        .accent-text { color: #EAB308; font-weight: 900; }
        .tila-box { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 12px; text-align: center; }
        .tila-val { font-size: 20px; font-weight: 800; color: #0F172A; }
        .disclosure-notice { background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 12px; border-radius: 4px; font-size: 13px; color: #78350F; }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# Core Financial Calculation Matrix Engine Framework
# ----------------------------------------------------
def calculate_apr(principal, fee, emi, tenure):
    net_received = principal - fee
    if net_received <= 0 or emi <= 0:
        return 0.0
    r = 0.01  # Newton-Raphson initial numerical approximation guess value
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

# ----------------------------------------------------
# Dynamic Route State Navigation Framework Menu Tab Layer
# ----------------------------------------------------
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Lender Admin Setup"

# Read incoming query URL targets safely if someone opens a generated borrower link
query_params = st.query_params
if "view" in query_params and query_params["view"] == "borrower":
    st.session_state["view_mode"] = "Borrower Portal E-Sign"

# Brand Top Header Banner View Layout Section
col_logo, col_trust = st.columns([2, 1])
with col_logo:
    st.markdown('<div class="main-header">✨ Advance <span class="accent-text">America</span></div>', unsafe_allow_html=True)
with col_trust:
    st.markdown("<div style='text-align: right; font-size: 11px; font-weight: bold; color: #94A3B8; margin-top:10px;'>FDIC INSURED • BBB A+ RATED</div>", unsafe_allow_html=True)

st.divider()

# ----------------------------------------------------
# MODE 1: LENDER ADMIN CONFIGURATION SETUP SCREEN
# ----------------------------------------------------
if st.session_state["view_mode"] == "Lender Admin Setup":
    st.subheader("📋 Loan Agreement Generation Console")
    st.caption("Input borrower parameters to compile custom digital credit contracts.")

    with st.form("lender_generation_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Borrower Full Name", value="John Doe")
            email = st.text_input("Borrower Email Address", value="borrower@example.com")
            bank = st.text_input("Disbursement Bank Info", value="Chase Bank (Acc: *******5678)")
        with col2:
            address = st.text_input("Physical Address Location", value="123 Main Street, Los Angeles, CA")
            amount = st.number_input("Loan Principal Amount ($)", min_value=1000, max_value=100000, value=5000, step=500)
            tenure = st.slider("Loan Repayment Tenure (Months)", min_value=12, max_value=60, value=24)
            
        first_payment_date = st.date_input("First Monthly Due Milestone Date", datetime.today())
        submit_btn = st.form_submit_button("Compile Secure Borrower Contract Link")

    if submit_btn:
        # Build encrypted/structured tracking queries parameter extension string link strings
        params = f"?view=borrower&n={name.replace(' ', '+')}&a={address.replace(' ', '+')}&b={bank.replace(' ', '+')}&p={amount}&t={tenure}&d={first_payment_date.strftime('%Y-%m-%d')}"
        base_url = "http://localhost:8501/" # Swap to your deployment server link upon production rollout launch
        shareable_link = base_url + params
        
        st.success("🎉 Secure Signature Link Generated Successfully!")
        st.code(shareable_link, language="text")
        st.info("Copy the generated framework string web route path link configuration block rule above and message it to your borrower client profile.")

# ----------------------------------------------------
# MODE 2: BORROWER SIGNING PANEL & CONTRACT CONSOLE VIEW
# ----------------------------------------------------
elif st.session_state["view_mode"] == "Borrower Portal E-Sign":
    # Parse parameter data metrics strings directly out of the query links securely
    p_name = query_params.get("n", "Borrower")
    p_addr = query_params.get("a", "N/A")
    p_bank = query_params.get("b", "N/A")
    p_principal = float(query_params.get("p", 0))
    p_tenure = int(query_params.get("t", 12))
    p_date_str = query_params.get("d", datetime.today().strftime("%Y-%m-%d"))

    # Financial Underwriting Formula Execution Layer Blocks
    fee = p_principal * 0.025
    total_interest = p_principal * 0.08 * (p_tenure / 12)
    total_repayment = p_principal + total_interest
    emi = total_repayment / p_tenure
    apr = calculate_apr(p_principal, fee, emi, p_tenure)

    start_date = datetime.strptime(p_date_str, "%Y-%m-%d")
    
    st.subheader("📜 Digital Promissory Note & Commercial Credit Instrument")
    st.caption("Review terms below, complete the dynamic interactive validation e-signature input process to execute contract distribution rules.")

    # High Fidelity Truth-in-Lending Act Grid Matrix
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="tila-box"><div>GROSS PRINCIPAL</div><div class="tila-val">${p_principal:,.2f}</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="tila-box"><div>ANNUAL PERCENTAGE APR</div><div class="tila-val" style="color:#D97706;">{apr:.2f}%</div></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="tila-box"><div>MONTHLY EMI DUE</div><div class="tila-val" style="color:#2563EB;">${emi:,.2f}</div></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="tila-box"><div>TOTAL COST OF LOAN</div><div class="tila-val">${total_repayment:,.2f}</div></div>', unsafe_allow_html=True)

    st.write("")

    # Agreement Legal Framework Body Text
    st.markdown(f"""
    This dynamic electronic financing covenant outlines binding rules governing account distributions executed between **Advance America Financial Outlets** (Lender) and **{p_name}** (Borrower), residing at location destination **{p_addr}**.
    
    * **1. Fees & Distribution Protocols:** The net principal threshold is defined as **${p_principal:,.2f}**. An operational processing capitalization fee of **2.50%** (**${fee:,.2f}**) is calculated and bundled natively into the standard loan tracking matrix. Disbursements automatically clear down to the routing track at **{p_bank}**.
    * **2. Interest Structuring Rule:** Interest accumulation traces structural intervals mapped precisely against a fixed baseline **8.00% annual flat rate yield index constraint**. Total interest yield over the note length of **{p_tenure} months** equals **${total_interest:,.2f}**.
    """)

    st.markdown(f"""
    <div class="disclosure-notice">
        ⚠️ <strong>UNDERWRITING CAPACITY CREDIT RISK MARKER NOTICE:</strong> Final validation approvals and account transaction settlement releases remain contingent on the verification of active debt capabilities and background security metrics. Systemic defaults will generate immediate negative markers onto credit tracking reporting platforms.
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.markdown("#### 📅 Amortization Payment Milestone Breakdown Schedule")

    # Dynamic Schedule Matrix Compilation Loop Engine Block
    amortization_rows = []
    running_balance = total_repayment
    p_step = p_principal / p_tenure
    i_step = total_interest / p_tenure
    current_date = start_date

    for idx in range(1, p_tenure + 1):
        running_balance -= emi
        amortization_rows.append([
            idx,
            current_date.strftime("%b %d, %Y"),
            f"${emi:,.2f}",
            f"${p_step:,.2f}",
            f"${i_step:,.2f}",
            f"${max(0.0, running_balance):,.2f}"
        ])
        current_date += relativedelta(months=1)

    df_schedule = pd.DataFrame(amortization_rows, columns=["Month #", "Due Date Milestone", "Installment (EMI)", "Principal Share", "Flat Interest", "Remaining Balance"])
    st.dataframe(df_schedule, use_container_width=True, hide_index=True)

    st.divider()

    # Interactive Signature Box Layout
    col_sig, col_download = st.columns([2, 1])
    with col_sig:
        st.markdown("##### 🖋️ Secure Borrower Attestation E-Sign Pad Zone")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#F8FAFC",
            height=120,
            width=400,
            drawing_mode="freedraw",
            key="signature_pad",
        )
    
    with col_download:
        st.markdown("##### 🖨️ Contract Finalization")
        st.caption("Once you sign cleanly within the touch capture canvas window, print or save a record tracking copy directly below.")
        
        # Verify canvas payload interactions to check for user signature execution status
        if canvas_result.image_data is not None and canvas_result.image_data.any():
            # Standard formatting logic configuration rule enabling print output capture structures
