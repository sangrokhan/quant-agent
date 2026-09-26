# Backtest Report: Equity Trend Gated by TLT's Own Strength vs MA (2026-09-26)

**Strategy file:** `strategies/2026-09-26_tlt_strength_gated_equity_trend.py`
**KB id:** 2026-09-26-016

## Hypothesis

Per QuantifiedStrategies.com's "Stocks vs. Bonds: What History Says When
Bonds Decline"
(https://quantifiedstrategies.substack.com/p/stocks-vs-bonds-what-history-says-when-bonds-decline,
free disclosed finding; full numeric trading-rule table paywalled, but the
core mechanic and one illustrative example fully disclosed): when TLT
trades below its own moving average (bonds weak/rates rising), subsequent
equity performance is historically weak (source's own 15-day-MA example:
421 trades since 2003, only 2.37% CAGR, 50% MDD staying invested during
TLT-below-MA). Source's own stated conclusion: "flipping the logic —
owning stocks when bonds are strong — produced significantly better
results." This strategy implements the flipped version directly: gate the
primary asset's own close>SMA(trend_window) trend-following signal to be
long ONLY when TLT itself is above its own rolling SMA(tlt_ma_window)
(bonds-strong regime); flat otherwise.

Distinct from every other TLT-based cross-asset gate in this repo
(SPY/TLT ratio SMA crossover 2026-09-05-036, TLT/IEF duration ratio
2026-09-11-045, GLD/TLT ratio 2026-09-11-031, Network Momentum single-edge
spillover 2026-09-08-143) — this uses TLT's own ABSOLUTE price level vs
its own MA (not a ratio against another asset, not a momentum/return
threshold), exactly the mechanic the source describes and recommends.

## Grid test (Step 6)

`trend_window` in {50, 100, 150} x `tlt_ma_window` in {10, 15, 25},
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto — falsification check, no
TLT-equity economic linkage expected), vol_regime_splits=3, 2016-2026
(108 cells):

- **pass_fraction = 0.519 (56/108) — the highest of any strategy tested
  this cron trigger**
- by_asset_class: equity 33/54, crypto 23/54 (crypto surprisingly strong
  on the grid too — likely reflects that TLT-strength happens to coincide
  with broad risk-on macro conditions that also favor crypto, though this
  should be treated cautiously per the MDD result below)
- by_vol_regime: low 30/36, mid 20/36, high 6/36
- best_cell: `trend_window=100, tlt_ma_window=25`, QQQ, low-vol, Sharpe 2.595
- worst_cell: `trend_window=150, tlt_ma_window=25`, ETH/USDT, high-vol,
  Sharpe -0.309

Full local 9-combo sweep on all 4 symbols confirms QQQ and SPY clear
Sharpe>=1.0 at MOST tested combos (QQQ: 7/9 combos ≥1.0; SPY: 5/9 combos
≥1.0), while BTC/USDT and ETH/USDT have strong Sharpe (often >1.0) but
consistently fail max_drawdown (0.27-0.65, well above the 0.25 threshold)
— crypto's own volatility swamps the TLT-gate's risk reduction.

## Single-config validation (Step 7)

Config: `trend_window=50, tlt_ma_window=25`, full sample 2016-2026.

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | **1.534** (pass, ≥1.0) | 1.183 (pass, ≥1.0) |
| Max Drawdown | 0.121 (pass, ≤0.25) | 0.090 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 1.239 (pass, ≥0.5) | 0.735 (pass, ≥0.5) |
| Walk-forward (manual 4-split) | 1.0 (pass, ≥0.75) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std, 9-cell) | 0.119 (pass, ≤0.5) | 0.141 (pass, ≤0.5) |
| num_trades | 144 | 161 |

## Decision

**ACCEPT for both QQQ and SPY** (all 5 validators pass for both symbols —
the second strategy this cron trigger to be accepted for BOTH primary
equity tickers, and the strongest overall grid pass fraction of any
strategy tested this trigger). **REJECT for crypto** (BTC/USDT and
ETH/USDT show attractive Sharpe on the grid but decisively fail
max_drawdown full-sample at every tested config — TLT's macro-regime
signal does not sufficiently cap crypto's own volatility-driven drawdowns,
consistent with this repo's general finding that TLT/bond-market signals
don't reliably transfer to crypto).

## Source

https://quantifiedstrategies.substack.com/p/stocks-vs-bonds-what-history-says-when-bonds-decline
(free, partially disclosed — core mechanic + one illustrative 15-day-MA
example free; the full parameter-sweep table paywalled) — read via
`browser_exec`.
