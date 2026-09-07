# Backtest Report: Vervoort Volatility Band 3-Candle Long-Only Reversal

**Strategy file:** `strategies/2026-09-08_vervoort_volband_3candle_reversal.py`
**Date:** 2026-09-08
**Outcome:** REJECTED

## Hypothesis

Per marketcalls.in's "Volatility Band – Long Only Reversal Trading System"
(https://www.marketcalls.in/amibroker/volatility-band-long-only-reversal-trading-system.html,
retrieved via Google's AI-overview summary of the page since the original
URL 404'd this iteration), a 3-candle sequence signals an oversold reversal
around a Vervoort-style volatility band: candle 1 closes below the lower
band, candle 2 closes back above the lower band, candle 3 closes higher
than candle 2 -> long entry. Since the exact Vervoort band formula source
(TradingView LazyBear Pine script, thinkorswim docs) also 404'd this
iteration, the band was approximated as EMA(basis_window) of typical price
+/- atr_mult * ATR(atr_window) (a Keltner-style smoothed band consistent
with the source's "highly smoothed data" description of Vervoort's style).

First 3-candle price-action pattern strategy built around a volatility band
in this repo — distinct from two other Vervoort-attributed indicators
already tested here (2026-09-06-114 Inverse Fisher Transform of Stochastic,
2026-09-06-119 Zero-Lag Rainbow %B), which are oscillator threshold/crossover
systems, not a raw close-sequence pattern trigger.

## Grid Test Summary (Step 6)

`param_grid={"atr_mult": [1.5, 2.0, 2.5], "max_hold_days": [5, 10]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **72 total cells, 2 passed (pass_fraction = 0.028)**
- By asset class: equity 2/36, crypto 0/36 (decisive crypto fail)
- By vol regime: low 0/24, mid 2/24, high 0/24 (edge, if any, concentrated
  in mid-vol only)
- Best cell: `atr_mult=2.0, max_hold_days=10`, QQQ mid-vol, Sharpe 1.60
- Worst cell: `atr_mult=1.5, max_hold_days=5`, SPY high-vol, Sharpe -0.88

## Single-Config Validation (Step 7, best-cell config on QQQ full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.33 | 1.00 |
| Max drawdown | **FAIL** | 24.8% | 25% |

Full-sample Sharpe fails decisively, and max drawdown is right at the
threshold edge (fail). The apparent mid-vol-only edge in the grid does not
survive a full-sample check on its own best symbol/config. Walk-forward and
parameter-sensitivity skipped given the already-decisive fail on both
Sharpe and drawdown, and the very low overall grid pass fraction (2.8%).

## Decision

**REJECTED.** Both Sharpe and max-drawdown fail full-sample on the
best-looking grid cell; grid pass fraction is very low (2/72) with no
consistent asset-class/regime concentration to justify a narrower accept;
crypto rejected decisively (0/36).
