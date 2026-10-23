import calendar
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Installment Loan Agreement Generator", page_icon="📄", layout="centered")

LENDER_DEFAULT = "Harborline Credit (SAMPLE)"
FEE_RATE = 0.025        # administrative processing fee, % of principal
ANNUAL_RATE = 0.08      # flat annual interest


def add_months(d: date, n: int) -> date:
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def money(x: float) -> str:
    return f"${x:,.2f}"


def solve_apr(net: float, emi: float, months: int) -> float:
    """Newton-Raphson on the monthly rate; returns nominal APR (monthly rate x 12)."""
    i = 0.01
    for _ in range(200):
        f = sum(emi / (1 + i) ** k for k in range(1, months + 1)) - net
        df = sum(-k * emi / (1 + i) ** (k + 1) for k in range(1, months + 1))
        nxt = i - f / df
        if abs(nxt - i) < 1e-14:
            i = nxt
            break
        i = nxt
    return i * 12


def build(principal: float, months: int, first: date):
    fee = principal * FEE_RATE
    interest = principal * ANNUAL_RATE * months / 12
    emi = (principal + interest) / months
    net = principal - fee
    apr = solve_apr(net, emi, months)
    rows, bal = [], principal + interest
    for k in range(months):
        bal = max(bal - emi, 0.0)
        if abs(bal) < 1e-9:
            bal = 0.0
        rows.append(
            {
                "Month": k + 1,
                "Due date": add_months(first, k).strftime("%b %d, %Y"),
                "Total payment": emi,
                "Principal share": principal / months,
                "Interest share": interest / months,
                "Remaining balance": bal,
            }
        )
    return dict(fee=fee, interest=interest, emi=emi, net=net, apr=apr,
                total=emi * months, finance_charge=interest + fee,
                last=add_months(first, months - 1)), pd.DataFrame(rows)


st.warning("SAMPLE TEMPLATE. Not a real loan offer. A real lender must use its own name, licensing and legal review.")
st.title("Installment Loan Agreement Generator")

with st.sidebar:
    st.header("Loan inputs")
    lender = st.text_input("Lender name", LENDER_DEFAULT)
    principal = st.number_input("Principal ($)", min_value=100.0, max_value=100000.0, value=5000.0, step=100.0)
    months = st.slider("Term (months)", 3, 60, 12)
    today = date.today()
    first = st.date_input("First payment date", value=add_months(today, 1))

st.subheader("Borrower details")
c1, c2 = st.columns(2)
name = c1.text_input("Full name", "Jordan A. Sample")
email = c2.text_input("Email", "jordan.sample@example.com")
address = st.text_input("Address", "100 Example Street, Sampletown, ST 00000")
st.caption("Do not enter real bank account or routing numbers here. Collecting them needs proper security, encryption and compliance work.")

r, df = build(principal, months, first)

st.subheader("Federal loan disclosures")
a, b = st.columns(2)
a.metric("APR", f"{r['apr'] * 100:.2f}%")
b.metric("Finance charge", money(r["finance_charge"]))
a.metric("Amount financed", money(r["net"]))
b.metric("Total of payments", money(r["total"]))

st.write(
    f"Monthly payment **{money(r['emi'])}** for **{months}** months. "
    f"First payment **{first.strftime('%B %d, %Y')}**, final payment **{r['last'].strftime('%B %d, %Y')}**. "
    f"Processing fee {money(r['fee'])} is deducted from proceeds."
)

st.subheader("Payment schedule")
st.dataframe(
    df.style.format({c: "${:,.2f}" for c in df.columns if c not in ("Month", "Due date")}),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Credit evaluation and capacity")
st.info(
    f"IMPORTANT DISCLOSURE ON CREDIT EVALUATION AND CAPACITY: {lender} uses credit reporting "
    "verification systems to evaluate consumer risk. Final funding authorization and release of funds "
    "remain contingent on a real-time review of the borrower's recurring debt-to-income performance. "
    "Default events will trigger reporting of derogatory marks to credit bureaus."
)

st.subheader("Borrower e-sign zone")
with st.container(border=True):
    sig = st.text_input("Type full name to sign")
    agree = st.checkbox("I have read the disclosures and terms and agree to sign electronically.")
    signed = bool(agree and len(sig.strip()) >= 3)
    if signed:
        st.markdown(f"### _{sig.strip()}_")
        st.success("Signature captured. Download unlocked.")
    else:
        st.error("Download is locked until an electronic signature has been captured.")

    text = f"""{lender.upper()} - INSTALLMENT LOAN AGREEMENT (SAMPLE)
Borrower: {name} | {email} | {address}
Principal: {money(principal)} | Fee: {money(r['fee'])} | Net cash: {money(r['net'])}
Flat interest (8%): {money(r['interest'])} | Monthly payment: {money(r['emi'])} x {months}
APR: {r['apr'] * 100:.2f}% | Finance charge: {money(r['finance_charge'])} | Total of payments: {money(r['total'])}
First payment: {first:%B %d, %Y} | Final payment: {r['last']:%B %d, %Y}

SCHEDULE
{df.to_csv(index=False)}
Signed electronically by: {sig.strip() if signed else '[unsigned]'}
"""
    st.download_button("Download signed copy", text, file_name="loan_agreement_sample.txt", disabled=not signed)
