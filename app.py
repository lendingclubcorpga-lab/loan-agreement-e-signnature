from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math

app = Flask(__name__, template_folder='templates')

def calculate_apr(principal, fee, emi, tenure):
    net_received = principal - fee
    if net_received <= 0 or emi <= 0:
        return 0.0
    
    # Newton-Raphson method for exact monthly rate conversion
    r = 0.01
    for _ in range(100):
        f = 0
        df = 0
        for m in range(1, tenure + 1):
            f += emi / ((1 + r) ** m)
            df -= (m * emi) / ((1 + r) ** (m + 1))
        f -= net_received
        if df == 0:
            break
        r_next = r - f / df
        if abs(r_next - r) < 1e-6:
            r = r_next
            break
        r = r_next
        
    return r * 12 * 100

@app.route('/')
def home():
    # Detect query parameters to determine view route context mapping rules
    is_borrower = request.args.get('view') == 'borrower'
    
    if is_borrower:
        try:
            # Parse parameters passed from lender dashboard setup configurations
            p = float(request.args.get('p', 0))
            t = int(request.args.get('t', 12))
            name = request.args.get('n', '')
            addr = request.args.get('a', '')
            bank = request.args.get('b', '')
            first_date_str = request.args.get('d', '')
            
            # 8% Flat Interest & 2.5% Processing Fee Calculations
            fee = p * 0.025
            total_interest = p * 0.08 * (t / 12)
            total_repayment = p + total_interest
            emi = total_repayment / t
            apr = calculate_apr(p, fee, emi, t)
            
            # Build amortization table data list matrix
            amortization_schedule = []
            running_balance = total_repayment
            p_step = p / t
            i_step = total_interest / t
            
            start_date = datetime.strptime(first_date_str, '%Y-%m-%d') if first_date_str else datetime.today()
            current_date = start_date
            
            for i in range(1, t + 1):
                running_balance -= emi
                if running_balance < 0.01:
                    running_balance = 0
                
                amortization_schedule.append({
                    'month': i,
                    'date': current_date.strftime('%b %d, %Y'),
                    'emi': f"${emi:,.2f}",
                    'principal': f"${p_step:,.2f}",
                    'interest': f"${i_step:,.2f}",
                    'balance': f"${running_balance:,.2f}"
                })
                current_date += relativedelta(months=1)
                
            paid_off_date = (current_date - relativedelta(months=1)).strftime('%B %d, %Y')
            
            return render_template('index.html', view='borrower', name=name, address=addr, bank=bank,
                                   principal=f"${p:,.2f}", fee=f"${fee:,.2f}", tenure=t,
                                   total_interest=f"${total_interest:,.2f}", emi=f"${emi:,.2f}",
                                   apr=f"{apr:.2f}%", total_cost=f"${total_repayment:,.2f}",
                                   first_date=start_date.strftime('%B %d, %Y'), paid_off_date=paid_off_date,
                                   schedule=amortization_schedule)
        except Exception:
            return "Invalid link payload matrix parameters configuration.", 400
            
    return render_template('index.html', view='lender')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
