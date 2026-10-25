import calendar
import base64
import io
import json
import os
import random
import re
import tempfile
import zlib
from datetime import date

import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from fpdf import FPDF

st.set_page_config(page_title="Loan Agreement Generator", page_icon="📄", layout="centered")

SIGNATURE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;padding:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
#wrap{padding:2px}
canvas{display:block;width:100%;height:180px;border:2px dashed #f59a1b;border-radius:6px;background:#fff;touch-action:none;cursor:crosshair;box-sizing:border-box}
.bar{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:6px;font-size:13px;color:#7a8799}
button{font:inherit;font-size:13px;padding:5px 14px;border-radius:4px;border:1px solid #9aa6b8;background:transparent;color:inherit;cursor:pointer}
button:focus-visible{outline:3px solid #f59a1b}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas>
<div class="bar"><span id="hint">Sign above with your finger or mouse</span><button id="clr" type="button">Clear</button></div></div>
<script>
(function(){
function post(m){m.isStreamlitMessage=true;window.parent.postMessage(m,"*");}
var cv=document.getElementById("c"),ctx=cv.getContext("2d"),hint=document.getElementById("hint");
var drawing=false,dirty=false,lastW=0;
function fit(){post({type:"streamlit:setFrameHeight",height:document.body.scrollHeight+6});}
function size(){
  var r=cv.getBoundingClientRect(),d=Math.min(window.devicePixelRatio||1,2);
  cv.width=Math.round(r.width*d);cv.height=Math.round(r.height*d);
  ctx.setTransform(d,0,0,d,0,0);ctx.lineWidth=2.4;ctx.lineCap="round";ctx.lineJoin="round";ctx.strokeStyle="#0c1b33";
  lastW=r.width;
}
function pos(e){var r=cv.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
function send(v){post({type:"streamlit:setComponentValue",value:v,dataType:"json"});}
function exportPng(){
  var o=document.createElement("canvas");o.width=cv.width;o.height=cv.height;
  var c=o.getContext("2d");c.fillStyle="#fff";c.fillRect(0,0,o.width,o.height);c.drawImage(cv,0,0);
  return o.toDataURL("image/png");
}
cv.addEventListener("pointerdown",function(e){
  e.preventDefault();cv.setPointerCapture(e.pointerId);drawing=true;
  var p=pos(e);ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+0.01,p.y+0.01);ctx.stroke();
});
cv.addEventListener("pointermove",function(e){
  if(!drawing)return;e.preventDefault();var p=pos(e);ctx.lineTo(p.x,p.y);ctx.stroke();ctx.beginPath();ctx.moveTo(p.x,p.y);
});
function up(){
  if(!drawing)return;drawing=false;dirty=true;hint.textContent="Signature captured. Draw again or press Clear to redo.";send(exportPng());
}
cv.addEventListener("pointerup",up);cv.addEventListener("pointercancel",up);
document.getElementById("clr").addEventListener("click",function(){
  ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,cv.width,cv.height);ctx.restore();
  dirty=false;hint.textContent="Sign above with your finger or mouse";send(null);
});
window.addEventListener("message",function(e){
  if(e.data&&e.data.type==="streamlit:render"){
    if(Math.abs(cv.getBoundingClientRect().width-lastW)>2){size();if(dirty){dirty=false;send(null);}}
    fit();
  }
});
window.addEventListener("resize",function(){if(Math.abs(cv.getBoundingClientRect().width-lastW)>2){size();if(dirty){dirty=false;hint.textContent="Sign above with your finger or mouse";send(null);}}});
size();
post({type:"streamlit:componentReady",apiVersion:1});fit();
})();
</script></body></html>
"""

_sig_dir = Path(tempfile.gettempdir()) / "signature_pad_v1"
_sig_dir.mkdir(parents=True, exist_ok=True)
(_sig_dir / "index.html").write_text(SIGNATURE_HTML, encoding="utf-8")
sig_pad = components.declare_component("signature_pad", path=str(_sig_dir))

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


def solve_apr(net, payments):
    """Newton-Raphson on the monthly rate for the actual payment stream; APR = monthly rate x 12."""
    i = 0.01
    for _ in range(200):
        f = sum(p / (1 + i) ** k for k, p in enumerate(payments, 1)) - net
        df = sum(-k * p / (1 + i) ** (k + 1) for k, p in enumerate(payments, 1))
        nxt = i - f / df
        if abs(nxt - i) < 1e-14:
            i = nxt
            break
        i = nxt
    return i * 12


def build(principal, months, first, rate=ANNUAL_RATE, method="reducing"):
    fee = principal * FEE_RATE
    net = principal - fee
    rows = []
    if method == "flat":
        interest = principal * rate * months / 12
        emi = (principal + interest) / months
        bal = principal + interest
        for k in range(months):
            bal = max(bal - emi, 0.0)
            if abs(bal) < 1e-9:
                bal = 0.0
            rows.append([k + 1, add_months(first, k).strftime("%b %d, %Y"), emi, principal / months, interest / months, bal])
    else:
        i = rate / 12
        emi = principal / months if i == 0 else principal * i / (1 - (1 + i) ** -months)
        bal, interest = principal, 0.0
        for k in range(months):
            it = bal * i
            pr = emi - it
            bal = max(bal - pr, 0.0)
            if abs(bal) < 1e-9:
                bal = 0.0
            interest += it
            rows.append([k + 1, add_months(first, k).strftime("%b %d, %Y"), emi, pr, it, bal])
    total = emi * months
    apr = solve_apr(net, [emi] * months)
    r = dict(method=method, rate=rate, fee=fee, interest=interest, emi=emi, net=net, apr=apr, total=total,
             finance_charge=interest + fee, total_cost=total + fee, last=add_months(first, months - 1))
    return r, rows


TERMS = [
    ("Promise to pay", "The Borrower promises to pay the Lender the Total of Payments shown in this Agreement in equal monthly installments on the due dates in the Payment Schedule."),
    ("Processing fee", "A one-time administrative processing fee is included in the financing and is deducted from the loan proceeds. It is part of the finance charge and is not refundable once funds are released."),
    ("Interest", "INTEREST_TEXT"),
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


INTEREST_TEXT = {
    "flat": "Interest is a flat rate calculated on the original principal for the full term. It does not reduce as installments are paid.",
    "reducing": "Interest accrues each month at the annual rate divided by twelve on the unpaid principal balance. Each installment first pays the interest accrued that month and the rest reduces principal, so the interest portion falls and the principal portion rises over the term.",
}


def terms_for(method):
    return [(t, INTEREST_TEXT[method] if body == "INTEREST_TEXT" else body) for t, body in TERMS]


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


def make_pdf(biz, lic, borrower, addr, email, principal, months, first, r, rows, signer, bank=""):
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
    if bank:
        kv(pdf, "Disbursement bank", bank)

    h(pdf, "2. Federal loan disclosures")
    for k, v in [("Annual percentage rate (APR)", f"{r['apr'] * 100:.2f}%"),
                 ("Finance charge (interest + fee)", money(r["finance_charge"])),
                 ("Amount financed (net cash to Borrower)", money(r["net"])),
                 ("Total of payments", money(r["total"]))]:
        kv(pdf, k, v)

    h(pdf, "3. Loan terms")
    for k, v in [("Principal", money(principal)),
                 ("Processing fee (2.50%, included in loan)", money(r["fee"])),
                 (f"Total interest ({r['rate'] * 100:.2f}% per year, {'flat' if r['method'] == 'flat' else 'reducing balance'})", money(r["interest"])),
                 ("Total repayment (principal + interest)", money(r["total"])),
                 ("Total cost of loan (repayment + fee)", money(r["total_cost"])),
                 ("Tenure", f"{months} months"),
                 ("Monthly installment", money(r["emi"])),
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
        if idx % 2:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
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
    for i, (t, body) in enumerate(terms_for(r["method"]), 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 5, f"5.{i} {t}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.8)
        pdf.multi_cell(0, 4.6, body, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)

    if pdf.get_y() > 220:
        pdf.add_page()
    h(pdf, "6. Signatures")
    y = pdf.get_y()
    pdf.image(io.BytesIO(signer), x=14, y=y, w=62)
    pdf.set_y(y + 22)
    pdf.set_draw_color(120, 130, 145)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 6, f"Borrower: {borrower}", border="T")
    pdf.cell(6, 6, "")
    pdf.cell(0, 6, f"Signed electronically on {date.today():%B %d, %Y}", border="T", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(95, 12, "", border="B")
    pdf.cell(6, 12, "")
    pdf.cell(0, 12, "", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 5, f"For the Lender: {biz}")
    return bytes(pdf.output())



def name_parts(full):
    t = full.split()
    return (t[0], t[-1] if len(t) > 1 else "") if t else ("", "")


def pdf_filename(full):
    first, last = name_parts(full)
    name = re.sub(r'[\\/:*?"<>|]+', "", f"{first} {last}").strip() or "Borrower"
    return f"Loan Agreement {name}.pdf"


def make_short(long_url, full_name):
    """Ask is.gd for a short link that includes the borrower's first and last name. Returns a URL or None."""
    import urllib.parse
    import urllib.request
    first, last = name_parts(full_name)
    clean = lambda x: re.sub(r"[^A-Za-z0-9]", "", x)
    base = "_".join(p for p in (clean(first), clean(last)) if p) or "Loan"
    if len(base) < 5:
        base = (base + "_Loan")[:30]
    base = base[:24]
    tries = [base, f"{base}_{random.randint(100, 999)}", f"{base}_{random.randint(1000, 9999)}", None]
    for alias in tries:
        api = "https://is.gd/create.php?format=simple&url=" + urllib.parse.quote(long_url, safe="")
        if alias:
            api += "&shorturl=" + alias
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "loan-agreement-app"})
            out = urllib.request.urlopen(req, timeout=10).read().decode().strip()
        except Exception as e:
            out = getattr(e, "read", lambda: b"")().decode(errors="ignore").strip() or "Error: unreachable"
        if out.startswith("http"):
            return out
        if "Error" in out and ("already" in out or "taken" in out or "short URL" in out) and alias:
            continue
        if "unreachable" in out:
            return None
    return None


def secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return None


FKEY = secret("FERNET_KEY")
ADMIN_PW = secret("ADMIN_PASSWORD")
APP_URL = (secret("APP_URL") or "").rstrip("/")
token = st.query_params.get("k") or st.query_params.get("t")


def pack(d):
    """Compact, encrypted, tamper-proof token (AES-GCM over zlib-compressed fields)."""
    p = d["principal"]
    raw = json.dumps([d["biz"], d["lic"], d["borrower"], d["email"], d["addr"], int(p) if p == int(p) else p,
                      d["months"], d["rate"], date.fromisoformat(d["first"]).toordinal(),
                      date.fromisoformat(d["exp"]).toordinal(),
                      "f" if d.get("method") == "flat" else "r", d.get("bank", "")], separators=(",", ":")).encode()
    nonce = os.urandom(12)
    ct = AESGCM(base64.urlsafe_b64decode(FKEY)).encrypt(nonce, zlib.compress(raw, 9), None)
    return base64.urlsafe_b64encode(nonce + ct).decode().rstrip("=")


def unpack(tok):
    b = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4))
    v = json.loads(zlib.decompress(AESGCM(base64.urlsafe_b64decode(FKEY)).decrypt(b[:12], b[12:], None)))
    return dict(biz=v[0], lic=v[1], borrower=v[2], email=v[3], addr=v[4], principal=v[5], months=v[6],
                rate=v[7], first=date.fromordinal(v[8]).isoformat(), exp=date.fromordinal(v[9]).isoformat(),
                method="reducing" if len(v) > 10 and v[10] == "r" else "flat",
                bank=v[11] if len(v) > 11 else "")


def summary(principal, months, first, r, rows):
    a, b, c = st.columns(3)
    a.metric("Monthly payment", money(r["emi"]))
    b.metric("APR", f"{r['apr'] * 100:.2f}%")
    c.metric("Net cash to borrower", money(r["net"]))
    a.metric("Processing fee (2.5%)", money(r["fee"]))
    b.metric("Total interest", money(r["interest"]))
    c.metric("Total repayment", money(r["total"]))
    a.metric("Total cost of loan", money(r["total_cost"]))
    b.metric("First payment", f"{first:%b %d, %Y}")
    c.metric("Payoff date", f"{r['last']:%b %d, %Y}")
    st.caption("Total cost of loan = total repayment + processing fee. "
               + ("Interest is charged on the remaining balance." if r["method"] == "reducing"
                  else "Interest is a flat amount on the original principal."))
    df = pd.DataFrame(rows, columns=["Month", "Due date", "Payment", "Principal", "Interest", "Balance"])
    st.dataframe(df.style.format({c: "${:,.2f}" for c in ["Payment", "Principal", "Interest", "Balance"]}),
                 hide_index=True, width="stretch")


# ---------------------------------------------------------------- borrower page
if token:
    if not FKEY:
        st.error("This signing page is not configured yet.")
        st.stop()
    try:
        try:
            d = unpack(token)
        except Exception:
            d = json.loads(Fernet(FKEY).decrypt(token.encode()))  # links made by the earlier version
    except Exception:
        st.error("This link is not valid. Ask the lender for a new one.")
        st.stop()
    if date.fromisoformat(d["exp"]) < date.today():
        st.error("This link has expired. Ask the lender for a new one.")
        st.stop()
    first = date.fromisoformat(d["first"])
    r, rows = build(d["principal"], d["months"], first, d.get("rate", 8.0) / 100, d.get("method", "flat"))
    st.title("Loan Agreement")
    st.caption(f"{d['biz']} - {d['lic']}")
    st.write(f"Prepared for **{d['borrower']}**. Please review everything below, then sign at the bottom.")
    if d.get("bank"):
        st.write(f"Disbursement bank: **{d['bank']}**")
    summary(d["principal"], d["months"], first, r, rows)
    with st.expander("Terms and conditions", expanded=False):
        for i, (t, body) in enumerate(terms_for(r["method"]), 1):
            st.markdown(f"**{i}. {t}**  \n{body}")
    st.subheader("Sign")
    with st.container(border=True):
        st.write("Draw your signature in the box with your finger or mouse.")
        sig = sig_pad(key="sig_pad", default=None)
        ok = st.checkbox("I have read the disclosures and terms and agree to sign electronically.")
        if ok and sig:
            st.success("Signature captured.")
            png = base64.b64decode(sig.split(",", 1)[1])
            pdf = make_pdf(d["biz"], d["lic"], d["borrower"], d["addr"], d["email"], d["principal"],
                           d["months"], first, r, rows, png, d.get("bank", ""))
            st.download_button("Download signed agreement (PDF)", pdf, file_name=pdf_filename(d["borrower"]), mime="application/pdf")
        else:
            st.info("Download unlocks after your signature is captured.")
    st.stop()

# ---------------------------------------------------------------- lender page
st.title("Loan Agreement Generator")
st.caption("Lender console. Enter your own business details. No third-party trust seals are added.")

if not (FKEY and ADMIN_PW):
    st.error("Setup needed: add ADMIN_PASSWORD and FERNET_KEY to the app's secrets (see README).")
    st.stop()
if st.text_input("Lender password", type="password") != ADMIN_PW:
    st.info("Enter the lender password to create agreement links.")
    st.stop()

with st.sidebar:
    st.header("Lender")
    biz = st.text_input("Business name", "Your Business Name")
    lic = st.text_input("License / registration no.", "License No. ____________")
    st.header("Loan")
    principal = st.number_input("Loan amount ($)", min_value=100.0, max_value=250000.0, value=5000.0, step=100.0)
    months = st.slider("Tenure (months)", 12, 60, 12)
    method_label = st.radio("Interest method", ["Reducing balance (standard)", "Flat rate"],
                            help="Reducing balance charges interest only on the unpaid balance. Flat charges it on the full principal for the whole term.")
    method = "reducing" if method_label.startswith("Reducing") else "flat"
    rate = st.number_input("Interest rate (% per year)", min_value=1.0, max_value=36.0, value=8.0, step=0.25,
                           help="Check the maximum rate allowed in your state.")
    first = st.date_input("First installment date", value=add_months(date.today(), 1), min_value=date.today())
    days = st.slider("Link valid for (days)", 1, 30, 7)

st.subheader("Borrower")
c1, c2 = st.columns(2)
borrower = c1.text_input("Full name")
email = c2.text_input("Email")
addr = st.text_input("Address")
bank = st.text_input("Bank name", help="The borrower's bank where funds will be sent. Bank name only; do not enter account numbers here.")

r, rows = build(principal, months, first, rate / 100, method)
summary(principal, months, first, r, rows)

st.subheader("Create signing link")
if st.button("Generate link", type="primary"):
    if not (borrower.strip() and email.strip() and addr.strip() and bank.strip() and biz.strip()):
        st.error("Fill in the business name and the borrower's name, email, address and bank name first.")
    else:
        payload = dict(biz=biz.strip(), lic=lic.strip(), borrower=borrower.strip(), email=email.strip(), bank=bank.strip(),
                       addr=addr.strip(), principal=principal, months=months, rate=rate, method=method, first=first.isoformat(),
                       exp=date.fromordinal(date.today().toordinal() + days).isoformat())
        tok = pack(payload)
        base = APP_URL or "https://YOUR-APP-URL.streamlit.app"
        long_url = f"{base}/?k={tok}"
        st.session_state["link"] = long_url
        st.session_state["short"] = make_short(long_url, borrower.strip())
if st.session_state.get("link"):
    short = st.session_state.get("short")
    if short:
        st.write("Send this link to the borrower:")
        st.code(short, language=None)
    else:
        st.warning("The short-link service could not be reached, so here is the full link. "
                   "You can paste it into tinyurl.com or bit.ly to shorten it.")
        st.code(st.session_state["link"], language=None)
    st.caption("The link is encrypted, cannot be edited, and expires on the date set. "
               "Signed copies are not stored here; the borrower downloads the PDF and should send it back to you.")
    if short:
        with st.expander("Full link (backup)"):
            st.code(st.session_state["link"], language=None)
