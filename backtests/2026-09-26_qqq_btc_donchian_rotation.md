# Backtest Report: QQQ-BTC Donchian Breakout Rotation with Cash Fallback (2026-09-26)

## Hypothesis
Source: QuantPedia's "Silicon vs. Satoshi: Tactical Asset Rotation Between
NASDAQ-100 and Bitcoin" (https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/,
browser_exec, own-research, Cyril Dujava, 2 July 2026, fully disclosed).

Three-state rotation among {primary equity, BTC, cash} using a Donchian
price-channel breakout: `U_t(w) = max(close[t-w:t-1])`; breakout when
`close_t > U_t(w)`. Variant A (source's own risk-adjusted-best): check the
primary equity for breakout first (hold it if so); else check BTC (hold BTC
if so); else hold cash (0% return). Source's own 2019-2025 QQQ+BTC result:
Sharpe 1.15-1.69 across w in {5,...,50} days, MDD -16.5% to -26.6%, all
beating a 50/50 QQQ/BTC buy-and-hold benchmark (Sharpe 1.19, MDD -59%).

First QQQ/SPY-BTC Donchian-rotation-with-cash-fallback strategy in this
repo. Tested with QQQ as primary (matching source exactly) and SPY as
primary (a natural variant of the same mechanic).

## Grid test summary (Step 6)

`lookback_window in {5,10,20,25,30,50}`, QQQ/SPY as primary asset (BTC/USDT
fetched internally for the second leg), `vol_regime_splits=3`, 2019-01-01
to 2026-09-01:

- `pass_fraction = 0.694` (25/36) -- by far the strongest grid pass fraction
  of any strategy tested this cron trigger
- `by_vol_regime`: low 9/12, mid 5/12, high 11/12 -- notably the HIGH-vol
  tercile has the strongest pass rate, the opposite of the usual
  vol-regime-slicing-mirage pattern seen elsewhere in this repo (this
  strategy's cash-fallback mechanism is specifically designed to shine
  during volatile/crash periods by sidestepping consolidation)
- `best_cell`: lookback_window=20, QQQ, high-vol, Sharpe 2.051

Full local 6-value full-sample sweep: QQQ Sharpe 1.309-1.805 (clears 1.0 at
every single tested lookback); SPY-as-primary also strong (see validators
below).

## Single-config validation (Step 7)

Config: `lookback_window=20` (source's own favored balance of Sharpe/Calmar).

| Metric | QQQ (primary) | SPY (primary) | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.651 (pass) | 1.221 (pass) | >= 1.0 |
| Max drawdown | 0.174 (pass) | 0.169 (pass) | <= 0.25 |
| TC survival (net Sharpe, 10bps/trade) | 0.969 (pass, near threshold at high turnover) | 0.535 (pass, thin) | >= 0.5 |
| Walk-forward (4 splits) | 1.00 (pass) | 1.00 (pass) | >= 0.75 |
| Parameter sensitivity (rel. std, 6-cell grid) | 0.096 (pass) | 0.172 (pass) | <= 0.5 |

Trade count is high (QQQ 529, SPY 585 state-changes over ~7.7 years,
reflecting the strategy's frequent regime-switching between QQQ/BTC/cash),
which is why TC-survival is the tightest-passing validator (10bps/trade
assumed, reasonable for both equity and crypto legs) -- both symbols still
clear the 0.5 net-Sharpe bar, though SPY only narrowly (0.535).

## Decision: ACCEPTED (QQQ and SPY both, as primary asset paired with BTC)

All 5 validators pass for both symbols. Extremely low parameter sensitivity
for both (rel.std 0.096 QQQ / 0.172 SPY) confirms this is a genuinely
robust edge across the source's own tested lookback range, not an overfit
artifact -- consistent with the source's own "robust plateau" finding
across the 5-30 day range. This is the single strongest strategy (by grid
pass fraction) accepted this cron trigger.

Source: https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/
(browser_exec, own-research, free, Cyril Dujava).
