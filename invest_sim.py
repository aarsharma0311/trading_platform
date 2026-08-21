"""
invest_sim.py — SELF-CONTAINED dip-tilt investing simulation.

This ONE file runs the whole thing. No other project files needed.
Paste it anywhere, install two packages, and run:

    pip install yfinance numpy
    python3 invest_sim.py

It downloads real historical prices for your basket and shows how $20k
would have done across several very different market periods — good
years, bad years, a crash, and single months — so you see the RANGE of
outcomes, not one misleading number.

EDIT YOUR WEIGHTS in the block marked below.
"""

import numpy as np

# ═══════════════════════════════════════════════════════════════════════
# ║   👉  PORTFOLIO WEIGHTS — EDIT HERE (must total 100)  👈             ║
# ═══════════════════════════════════════════════════════════════════════
PORTFOLIO_WEIGHTS_PERCENT = {
    "VOO": 40,   # S&P 500 core (safe)
    "VTI": 25,   # total US market core (safe; ~85% overlaps VOO)
    "QQQ": 30,   # growth / tech tilt (riskier)
    "BND": 5,   # bond ballast (stable in crashes)
}
# ═══════════════════════════════════════════════════════════════════════

# ---- money + schedule ----
STARTING_CASH = 20_000.0
MONTHLY_CONTRIBUTION = 1_000.0
BUY_FREQUENCY_DAYS = 7          # buy weekly
BASELINE_SPEND_FRACTION = 0.05  # spend ~5% of available cash each buy

# ---- dip-tilt knobs ----
DIP_REFERENCE = "VOO"           # which ticker's trend defines "the market"
DIP_MA_WINDOW = 100             # long-term moving average length (days)
DIP_SENSITIVITY = 0.15          # extra multiplier per 1% below the MA
MAX_DIP_MULTIPLIER = 3.5        # ceiling on dip aggression
MIN_MULTIPLIER = 0.5            # floor when market is expensive

# ---- periods to test (label, start, end) ----
PERIODS = [
    ("2020 COVID crash+recovery", "2020-01-01", "2021-01-01"),
    ("2021 strong bull year",     "2021-01-01", "2022-01-01"),
    ("2022 bear market",          "2022-01-01", "2023-01-01"),
    ("2023 recovery year",        "2023-01-01", "2024-01-01"),
    ("Full run 2019-2024",        "2019-01-01", "2024-12-31"),
    ("One month: Jan 2022",       "2022-01-01", "2022-02-01"),
    ("One month: Jul 2022",       "2022-07-01", "2022-08-01"),
]


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
def _weights():
    total = sum(PORTFOLIO_WEIGHTS_PERCENT.values())
    if abs(total - 100) > 0.01:
        raise SystemExit(
            f"\n  Weights add up to {total}, not 100. Fix "
            f"PORTFOLIO_WEIGHTS_PERCENT.\n  Current: {PORTFOLIO_WEIGHTS_PERCENT}\n")
    return {t: w / 100.0 for t, w in PORTFOLIO_WEIGHTS_PERCENT.items()}


TARGET_WEIGHTS = _weights()
TICKERS = list(TARGET_WEIGHTS.keys())


# ---------------------------------------------------------------------------
# data loading (yfinance) — returns dict[ticker] -> list of daily closes
# ---------------------------------------------------------------------------
def load_closes(start, end):
    import yfinance as yf
    out = {}
    for t in TICKERS:
        df = yf.download(t, start=start, end=end, interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or len(df) == 0:
            out[t] = []
            continue
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        out[t] = [float(x) for x in df["Close"].tolist()]
    return out


# ---------------------------------------------------------------------------
# the strategy
# ---------------------------------------------------------------------------
def dip_multiplier(price, ma):
    if not ma or ma <= 0:
        return 1.0
    pct_below = (ma - price) / ma * 100.0
    mult = 1.0 + DIP_SENSITIVITY * pct_below
    return float(min(MAX_DIP_MULTIPLIER, max(MIN_MULTIPLIER, mult)))


def moving_average(closes, window):
    if len(closes) < window:
        return None
    return float(np.mean(closes[-window:]))


def simulate(closes, dip_enabled):
    """Run the buy-only strategy over aligned daily closes. Returns
    (final_value, total_contributed, avg_costs, mult_range, cash, final_prices)."""
    n = min(len(closes[t]) for t in TICKERS)
    if n == 0:
        return None
    aligned = {t: closes[t][-n:] for t in TICKERS}
    ref = aligned[DIP_REFERENCE]

    cash = STARTING_CASH
    contributed = STARTING_CASH
    shares = {t: 0.0 for t in TICKERS}
    cost = {t: 0.0 for t in TICKERS}

    dsb, dsc = BUY_FREQUENCY_DAYS, 0
    mults = []
    for i in range(n):
        dsc += 1
        if dsc >= 21:                    # ~monthly contribution
            cash += MONTHLY_CONTRIBUTION
            contributed += MONTHLY_CONTRIBUTION
            dsc = 0
        dsb += 1
        if dsb >= BUY_FREQUENCY_DAYS:
            dsb = 0
            if cash <= 1:
                continue
            baseline = BASELINE_SPEND_FRACTION * cash
            if dip_enabled:
                ma = moving_average(ref[:i + 1], DIP_MA_WINDOW)
                mult = dip_multiplier(ref[i], ma)
            else:
                mult = 1.0
            mults.append(mult)
            spend = min(baseline * mult, cash)
            for t in TICKERS:
                price = aligned[t][i]
                if price <= 0:
                    continue
                dollars = spend * TARGET_WEIGHTS[t]
                sh = dollars / price
                shares[t] += sh
                cost[t] += dollars
                cash -= dollars

    final_prices = {t: aligned[t][-1] for t in TICKERS}
    invested = sum(shares[t] * final_prices[t] for t in TICKERS)
    value = cash + invested
    avg_costs = {t: (cost[t] / shares[t] if shares[t] > 0 else 0) for t in TICKERS}
    mrange = (min(mults), max(mults)) if mults else (1.0, 1.0)
    return value, contributed, avg_costs, mrange, cash, final_prices


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("=" * 76)
    print(f"DIP-TILT INVESTING — RANGE OF OUTCOMES")
    print(f"Start ${STARTING_CASH:,.0f}  +${MONTHLY_CONTRIBUTION:,.0f}/mo   "
          f"Basket {PORTFOLIO_WEIGHTS_PERCENT}")
    print("=" * 76)
    print(f"{'Period':<28}{'Contributed':>13}{'DipTilt':>12}"
          f"{'PlainDCA':>12}{'Return':>9}")
    print("-" * 76)

    for label, start, end in PERIODS:
        closes = load_closes(start, end)
        if any(len(closes[t]) == 0 for t in TICKERS):
            print(f"{label:<28}  (no data — check connection)")
            continue
        dip = simulate(closes, dip_enabled=True)
        dca = simulate(closes, dip_enabled=False)
        if not dip or not dca:
            print(f"{label:<28}  (insufficient data)")
            continue
        v_dip, contributed = dip[0], dip[1]
        v_dca = dca[0]
        ret = (v_dip / contributed - 1) * 100 if contributed else 0
        print(f"{label:<28}{contributed:>13,.0f}{v_dip:>12,.0f}"
              f"{v_dca:>12,.0f}{ret:>8.1f}%")

    print("-" * 76)
    print("How to read this honestly:")
    print("  - 'Contributed' = money you put in. Bot never sells; value = what")
    print("    those contributions grew or shrank to.")
    print("  - Good years look great; the 2022 row loses money. BOTH are real.")
    print("  - The two one-month rows show how noisy a single month is.")
    print("  - DipTilt vs PlainDCA usually differ only modestly — the tilt is a")
    print("    small edge, not magic. Sometimes DCA wins.")
    print("  - NONE of this predicts the future. It shows the RANGE, not a forecast.")
    print("=" * 76)


if __name__ == "__main__":
    main()