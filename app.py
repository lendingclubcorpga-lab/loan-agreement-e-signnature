import calendar
from datetime import date

import pandas as pd
import streamlit as st
from fpdf import FPDF

st.set_page_config(page_title="Loan Agreement Generator", page_icon="📄", layout="centered")

NAVY = (12, 27, 51)
AMBER = (245, 154, 27)
FEE_RATE = 0.025
ANNUAL_RATE = 0.08


def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def money(x):
    return f"${x:,.2f}"


def solve_apr(net, emi, months):
    """Newton-Raphson on the monthly rate, APR = monthly rate x 12."""
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


def build(principal, months, first):
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
        rows.append([k + 1, add_months(first, k).strftime("%b %d, %Y"), emi, principal / months, interest / months, bal])
    r = dict(fee=fee, interest=interest, emi=emi, net=net, apr=apr, total=emi * months,
             finance_charge=interest + fee, last=add_months(first, months - 1))
    return r, rows


TERMS = [
    ("Promise to pay", "The Borrower promises to pay the Lender the Total of Payments shown in this Agreement in equal monthly installments on the due dates in the Payment Schedule."),
    ("Processing fee", "A one-time administrative processing fee is included in the financing and is deducted from the loan proceeds. It is part of the finance charge and is not refundable once funds are released."),
    ("Interest", "Interest is a flat rate calculated on the original principal for the full term. It does not reduce as installments are paid."),
    ("Credit evaluation and repayment capacity", "The Lender may review credit reports and the Borrower's income and debts to assess repayment capacity. Funding depends on that review and on the Borrower's ability to repay. The Lender may decline or cancel an application before funds are released."),
    ("Late payment", "If an installment is not received within the grace period stated by the Lender, the Lender may charge a late fee allowed by applicable law. Late fee amount: ____________ (Lender to complete)."),
    ("Prepayment", "The Borrower may prepay all or part of the loan at any time. Prepayment terms and any refund of unearned charges follow applicable law: ____________ (Lender to complete)."),
    ("Default", "The Borrower is in default if any installment is more than the stated number of days past due, if information given in the application is materially false, or if the Borrower becomes insolvent. On default the Lender may require immediate payment of the unpaid balance, subject to notice rights under applicable law."),
    ("Credit reporting", "The Lender may report the account and any default to consumer reporting agencies, which can lower the Borrower's credit score."),
    ("Collection costs", "Where permitted by law, the Borrower is responsible for reasonable collection costs and court costs on a defaulted account."),
    ("Electronic signature and records", "The Borrower agrees to sign and receive this Agreement electronically. An electronic signature has the same effect as a handwritten signature. The Borrower may request a paper copy."),
    ("Privacy and data", "The Lender uses the Borrower's personal information only to evaluate, service and collect this loan and as required by law."),
    ("Governing law", "This Agreement is governed by the laws of: ____________ (Lender to complete) and any applicable federal law, including the Truth in Lending Act."),
    ("Entire agreement and severability", "This is the complete agreement between the parties. If any part is found unenforceable, the rest remains in effect. Changes must be in writing and signed by both parties."),
]


class Doc(FPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 26, "F")
        self.set_fill_color(*AMBER)
        self.rect(0, 26, 210, 1.6, "F")
        self.set_xy(12, 7)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 7, self.biz, new_x="LMARGIN", new_y="NEXT")
        self.set_x(12)
        self.set_font("Helvetica", "", 8.5)
        self.cell(0, 5, self.lic, new_x="LMARGIN", new_y="NEXT")
        self.set_y(32)
        self.set_text_color(20, 32, 47)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 120, 135)
        self.cell(0, 6, f"{self.biz} - Loan Agreement - Page {self.page_no()}", align="C")


def h(pdf, text):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*AMBER)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 30, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(20, 32, 47)


def kv(pdf, k, v):
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(70, 6, k, border="B")
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 6, v, border="B", new_x="LMARGIN", new_y="NEXT")


def make_pdf(biz, lic, borrower, addr, email, principal, months, first, r, rows, signer):
    pdf = Doc(format="A4")
    pdf.biz, pdf.lic = biz, lic
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(True, 16)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, "Closed-End Installment Loan Agreement", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Date of agreement: {date.today():%B %d, %Y}", new_x="LMARGIN", new_y="NEXT")

    h(pdf, "1. Parties")
    kv(pdf, "Lender", biz)
    kv(pdf, "Borrower", borrower)
    kv(pdf, "Address", addr)
    kv(pdf, "Email", email)

    h(pdf, "2. Federal loan disclosures")
    for k, v in [("Annual percentage rate (APR)", f"{r['apr'] * 100:.2f}%"),
                 ("Finance charge", money(r["finance_charge"])),
                 ("Amount financed (net cash to Borrower)", money(r["net"])),
                 ("Total of payments", money(r["total"]))]:
        kv(pdf, k, v)

    h(pdf, "3. Loan terms")
    for k, v in [("Principal", money(principal)),
                 ("Processing fee (2.50%, included in loan)", money(r["fee"])),
                 ("Flat interest (8.00% per year)", money(r["interest"])),
                 ("Total cost of loan (interest + fee)", money(r["finance_charge"])),
                 ("Tenure", f"{months} months"),
                 ("Monthly installment (EMI)", money(r["emi"])),
                 ("First installment due", first.strftime("%B %d, %Y")),
                 ("Paid-off date (final installment)", r["last"].strftime("%B %d, %Y"))]:
        kv(pdf, k, v)

    h(pdf, "4. Payment schedule")
    widths = [14, 32, 34, 34, 34, 38]
    heads = ["Month", "Due date", "Payment", "Principal", "Interest", "Balance"]
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    for w, t in zip(widths, heads):
        pdf.cell(w, 7, t, border=0, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(20, 32, 47)
    pdf.set_font("Helvetica", "", 8.5)
    for idx, row in enumerate(rows):
        pdf.set_fill_color(245, 247, 250) if idx % 2 else pdf.set_fill_color(255, 255, 255)
        vals = [str(row[0]), row[1]] + [money(x) for x in row[2:]]
        for w, t in zip(widths, vals):
            pdf.cell(w, 6, t, fill=True, align="C")
        pdf.ln()
    pdf.set_font("Helvetica", "B", 8.5)
    tot = ["", "Totals", money(sum(x[2] for x in rows)), money(sum(x[3] for x in rows)), money(sum(x[4] for x in rows)), "$0.00"]
    for w, t in zip(widths, tot):
        pdf.cell(w, 6.5, t, border="T", align="C")
    pdf.ln(8)

    h(pdf, "5. Terms and conditions")
    for i, (t, body) in enumerate(TERMS, 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 5, f"5.{i} {t}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.8)
        pdf.multi_cell(0, 4.6, body, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    if pdf.get_y() > 235:
        pdf.add_page()
    h(pdf, "6. Signatures")
    pdf.set_font("Helvetica", "I", 20)
    pdf.cell(95, 12, signer, border="B")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(6, 12, "")
    pdf.cell(0, 12, f"Signed electronically on {date.today():%B %d, %Y}", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 5, f"Borrower: {borrower}")
    pdf.ln(10)
    pdf.cell(95, 12, "", border="B")
    pdf.cell(6, 12, "")
    pdf.cell(0, 12, "", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 5, f"For the Lender: {biz}")
    return bytes(pdf.output())


st.title("Loan Agreement Generator")
st.caption("Enter your own business details. This tool does not add any third-party trust seals.")

with st.sidebar:
    st.header("Lender")
    biz = st.text_input("Business name", "Your Business Name")
    lic = st.text_input("License / registration no.", "License No. ____________")
    st.header("Loan")
    principal = st.number_input("Loan amount ($)", min_value=100.0, max_value=250000.0, value=5000.0, step=100.0)
    months = st.slider("Tenure (months)", 12, 60, 12)
    first = st.date_input("First installment date", value=add_months(date.today(), 1), min_value=date.today())

st.subheader("Borrower")
c1, c2 = st.columns(2)
borrower = c1.text_input("Full name")
email = c2.text_input("Email")
addr = st.text_input("Address")

r, rows = build(principal, months, first)

st.subheader("Loan summary")
a, b, c = st.columns(3)
a.metric("Monthly EMI", money(r["emi"]))
b.metric("APR", f"{r['apr'] * 100:.2f}%")
c.metric("Total of payments", money(r["total"]))
a.metric("Processing fee", money(r["fee"]))
b.metric("Interest", money(r["interest"]))
c.metric("Net cash", money(r["net"]))
st.write(f"Total cost of loan **{money(r['finance_charge'])}**. First installment **{first:%B %d, %Y}**. Paid off **{r['last']:%B %d, %Y}**.")

df = pd.DataFrame(rows, columns=["Month", "Due date", "Payment", "Principal", "Interest", "Balance"])
st.dataframe(df.style.format({c: "${:,.2f}" for c in ["Payment", "Principal", "Interest", "Balance"]}),
             hide_index=True, use_container_width=True)

st.subheader("Borrower signature")
with st.container(border=True):
    sig = st.text_input("Type full legal name to sign")
    ok = st.checkbox("I have read the disclosures and terms and agree to sign electronically.")
    ready = bool(borrower.strip() and email.strip() and addr.strip() and ok and len(sig.strip()) >= 3)
    if ready:
        st.success("Signature captured.")
        pdf = make_pdf(biz, lic, borrower.strip(), addr.strip(), email.strip(), principal, months, first, r, rows, sig.strip())
        st.download_button("Download signed agreement (PDF)", pdf, file_name="loan_agreement.pdf", mime="application/pdf")
    else:
        st.info("Fill in the borrower details, tick the box and type your name. Download unlocks after the signature is captured.")
