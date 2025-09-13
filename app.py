from flask import Flask, render_template, request
from math import isfinite

app = Flask(__name__)

def to_float(x, default):
    try:
        v = float(x)
        if not isfinite(v):
            return default
        return v
    except:
        return default

@app.route("/", methods=["GET", "POST"])
def index():
    # Default parameters (sensible starting values)
    params = {
        "notional_usd": 2000000.0,
        "usd_rate_annual": 4.2,     # % per year
        "jpy_rate_annual": 1.6,     # % per year
        "option_premium_pct_per_month": 2.0,  # % of notional per month
        "spot_jpy_per_usd": 150.0,  # JPY per USD
        "months": 1.0
    }
    result = None
    scenarios = []

    if request.method == "POST":
        for k in params.keys():
            params[k] = to_float(request.form.get(k, params[k]), params[k])

        N = params["notional_usd"]
        months = params["months"]
        spot = params["spot_jpy_per_usd"]
        usd_rate = params["usd_rate_annual"] / 100.0
        jpy_rate = params["jpy_rate_annual"] / 100.0
        opt_prem_m = params["option_premium_pct_per_month"] / 100.0

        # Borrowing cost = notional * (usd_rate - jpy_rate) * (months/12)
        borrow_cost_usd = N * max(usd_rate - jpy_rate, 0.0) * (months / 12.0)
        borrow_cost_jpy = borrow_cost_usd * spot

        # Option cost = notional * opt_prem_m * months
        option_cost_usd = N * opt_prem_m * months
        option_cost_jpy = option_cost_usd * spot

        # Threshold where Option becomes better THAN Borrowing
        # Solve: (ΔJPY * N) - option_cost_jpy > - borrow_cost_jpy  ->  ΔJPY > (option_cost_jpy - borrow_cost_jpy)/N
        delta_jpy_vs_borrow = (option_cost_jpy - borrow_cost_jpy) / N

        # Threshold where Option breaks even (vs zero): (ΔJPY * N) - option_cost_jpy > 0  ->  ΔJPY > option_cost_jpy / N
        delta_jpy_breakeven = option_cost_jpy / N

        # Build scenario table for a range of yen depreciation/appreciation
        # We'll show from -5 to +5 JPY moves around spot (negative = yen高, positive = 円安)
        moves = [-5,-4,-3,-2,-1,0,1,2,3,4,5]
        for d in moves:
            # Option payoff: max(ΔJPY, 0) * N  (using simplified linear model aligned with prior discussion)
            # NOTE: This follows the user's earlier framing for intuitive comparison.
            option_payoff_jpy = max(d, 0.0) * N
            option_pnl_jpy = option_payoff_jpy - option_cost_jpy

            # Borrowing PnL is always -borrow_cost_jpy (locked-in hedge)
            borrow_pnl_jpy = -borrow_cost_jpy

            better = "オプション" if option_pnl_jpy > borrow_pnl_jpy else ("借入" if option_pnl_jpy < borrow_pnl_jpy else "同等")

            scenarios.append({
                "move": d,
                "option_pnl_jpy": option_pnl_jpy,
                "borrow_pnl_jpy": borrow_pnl_jpy,
                "better": better
            })

        result = {
            "borrow_cost_usd": borrow_cost_usd,
            "borrow_cost_jpy": borrow_cost_jpy,
            "option_cost_usd": option_cost_usd,
            "option_cost_jpy": option_cost_jpy,
            "delta_jpy_vs_borrow": delta_jpy_vs_borrow,
            "delta_jpy_breakeven": delta_jpy_breakeven,
        }

    return render_template("index.html", params=params, result=result, scenarios=scenarios)

if __name__ == "__main__":
    # For local run
    app.run(host="0.0.0.0", port=5000, debug=True)
