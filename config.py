"""
Configuration for the dip-tilt long-term investing strategy.

This is a BUY-ONLY, long-horizon investing system — deliberately different
from the day-trading agent. No stops, no shorts, no intraday timing. It
deploys cash on a schedule and buys MORE when prices are below their
long-term trend ("buy the dip"), never selling.

Everything you'd reasonably want to change lives here.
"""

# ═══════════════════════════════════════════════════════════════════════
# ║                                                                     ║
# ║   👉  PORTFOLIO WEIGHTS — EDIT HERE  👈                              ║
# ║                                                                     ║
# ║   This is the ONE thing you'll change most. Numbers are PERCENTS.   ║
# ║   They MUST add up to 100. Change them, save, done.                 ║
# ║                                                                     ║
# ║   If an advisor says "less tech, more bonds", just edit the         ║
# ║   numbers below — e.g. drop QQQ to 20 and raise BND to 20.          ║
# ║                                                                     ║
# ║   To ADD a ticker: add a line (e.g. "SCHD": 10).                    ║
# ║   To REMOVE one:   delete its line.                                 ║
# ║   Just keep the total at 100 — the code checks this for you and     ║
# ║   will tell you if it's off.                                        ║
# ║                                                                     ║
# ╚═════════════════════════════════════════════════════════════════════
PORTFOLIO_WEIGHTS_PERCENT = {
    "VOO": 35,   # S&P 500 core (safe)
    "VTI": 25,   # total US market core (safe; ~85% overlaps VOO)
    "QQQ": 30,   # growth / tech tilt (riskier)
    "BND": 10,   # bond ballast (stable dry powder in crashes)
}
# ═══════════════════════════════════════════════════════════════════════
#   (Nothing below here needs to change to adjust your allocation.)
# ═══════════════════════════════════════════════════════════════════════


# --- validation + conversion (don't edit; this protects you from typos) ---
def _validate_and_normalize(weights_pct: dict) -> dict:
    if not weights_pct:
        raise ValueError("PORTFOLIO_WEIGHTS_PERCENT is empty — add at least one ticker.")
    total = sum(weights_pct.values())
    if abs(total - 100) > 0.01:
        raise ValueError(
            f"\n\n  ⚠ Your portfolio weights add up to {total}, not 100.\n"
            f"    Edit PORTFOLIO_WEIGHTS_PERCENT in investing/config.py so the\n"
            f"    numbers total 100. Current values: {weights_pct}\n")
    for t, w in weights_pct.items():
        if w < 0:
            raise ValueError(f"  ⚠ Weight for {t} is negative ({w}). Use 0–100.")
    return {t: w / 100.0 for t, w in weights_pct.items()}


# TARGET_WEIGHTS is what the rest of the code uses (fractions summing to 1.0).
# It's derived automatically from your percents above — don't edit it directly.
TARGET_WEIGHTS = _validate_and_normalize(PORTFOLIO_WEIGHTS_PERCENT)

# ---- Cash flow ----
# You deploy from an available-cash balance that you top up over time.
# The scheduler spends a baseline amount each period, scaled by dips.
STARTING_CASH = 20_000.0        # cash available to deploy at the start
MONTHLY_CONTRIBUTION = 1_000.0  # fresh cash you add each month (models your top-ups)

# ---- Schedule ----
# How often the bot buys. Weekly is a sensible default for DCA.
BUY_FREQUENCY_DAYS = 7          # buy every N calendar days

# Baseline spend per buy, as a fraction of *current available cash*.
# Using a fraction (not a fixed dollar amount) means it naturally slows
# as cash depletes and speeds up as contributions arrive — self-pacing,
# so you don't run dry. 0.05 = deploy ~5% of available cash each buy.
BASELINE_SPEND_FRACTION = 0.05

# ---- Dip tilt (the "buy more when cheap" logic) ----
# Cheapness is measured vs a long-term moving average of a reference index
# (default: VOO, i.e. the broad market). When price is below its MA, we buy
# MORE; when above, we buy LESS. This is smoother/more principled than
# reacting to daily moves or drawdown-from-peak.
DIP_REFERENCE = "VOO"           # which holding's trend defines "the market"
DIP_MA_WINDOW = 100             # trading days in the long-term moving average

# The tilt maps "percent below the MA" to a spend multiplier.
# At the MA (0% below): multiplier 1.0 (baseline).
# Each 1% below the MA adds DIP_SENSITIVITY to the multiplier.
# Above the MA, the multiplier drops (buys less when market is expensive),
# floored so we always keep investing something.
DIP_SENSITIVITY = 0.15          # multiplier added per 1% below the MA
MAX_DIP_MULTIPLIER = 3.5        # ceiling: never buy more than 3.5x baseline
MIN_MULTIPLIER = 0.5            # floor: even when expensive, still buy 0.5x

# ---- Alpaca (paper first!) ----
# Reuses the same Alpaca account pattern as the trading bot. Paper = fake
# money, real data/fills. Prove the mechanics here before ANY real money.
# All four tickers trade as normal equities/ETFs on Alpaca.
USE_FRACTIONAL_SHARES = True    # so weights stay clean regardless of price