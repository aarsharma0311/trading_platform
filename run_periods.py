"""
Range-of-outcomes runner.

Instead of ONE misleading "it makes X%" number, this runs your strategy
across several very different historical periods so you see the honest
SPREAD of what can happen — including the bad years. Same $20k, same
weights, wildly different results depending on what the market did.

    pip install yfinance pandas numpy
    python -m investing.run_periods

Add your own windows by editing PERIODS below.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investing.run_invest_backtest import _load_prices, _run
from investing import config as cfg


# (label, start, end) — a deliberately varied set: booms, busts, crashes, flat.
PERIODS = [
    ("2020 COVID crash + recovery", "2020-01-01", "2021-01-01"),
    ("2021 strong bull year",       "2021-01-01", "2022-01-01"),
    ("2022 bear market",            "2022-01-01", "2023-01-01"),
    ("2023 recovery year",          "2023-01-01", "2024-01-01"),
    ("Full multi-year run",         "2019-01-01", "2024-12-31"),
    ("One month (Jan 2022)",        "2022-01-01", "2022-02-01"),
    ("One month (Jul 2022 rally)",  "2022-07-01", "2022-08-01"),
]


def _pct(v, c):
    return (v / c - 1) * 100 if c else 0.0


def main():
    tickers = list(cfg.TARGET_WEIGHTS.keys())
    print("=" * 74)
    print(f"RANGE OF OUTCOMES — starting ${cfg.STARTING_CASH:,.0f}, "
          f"+${cfg.MONTHLY_CONTRIBUTION:,.0f}/mo")
    print(f"Basket: {cfg.PORTFOLIO_WEIGHTS_PERCENT}")
    print("=" * 74)
    print(f"{'Period':<32}{'Contributed':>13}{'DipTilt':>11}{'PlainDCA':>11}{'Return':>8}")
    print("-" * 74)

    for label, start, end in PERIODS:
        try:
            series = _load_prices(tickers, start, end, use_cache=True)
        except Exception as e:
            print(f"{label:<32}  data error: {e}")
            continue
        if any(len(series[t]) == 0 for t in tickers):
            print(f"{label:<32}  (no data — check connection)")
            continue

        pf_dip, _, final = _run(series, dip_enabled=True)
        pf_dca, _, _ = _run(series, dip_enabled=False)
        c = pf_dip.total_contributed
        v_dip = pf_dip.value(final)
        v_dca = pf_dca.value(final)
        print(f"{label:<32}{c:>13,.0f}{v_dip:>11,.0f}{v_dca:>11,.0f}"
              f"{_pct(v_dip, c):>7.1f}%")

    print("-" * 74)
    print("Reading this honestly:")
    print("  • 'Contributed' = money you put in (start + monthly). The bot never")
    print("    sells, so value = what your contributions grew or shrank to.")
    print("  • Good years look great; bad years lose money. BOTH are real. The")
    print("    single-month rows show how meaningless one month is — pure noise.")
    print("  • DipTilt vs PlainDCA usually differ only modestly. If they're close,")
    print("    that's the honest truth: the tilt is a small edge, not magic.")
    print("  • None of these predict the future. They show the RANGE, not a forecast.")
    print("=" * 74)


if __name__ == "__main__":
    main()