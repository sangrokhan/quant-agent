# ICT Optimal Trade Entry (OTE) 62%-79% Fibonacci Zone — Backtest Report (2026-09-24)

## Hypothesis

Per multiple corroborating ICT (Inner Circle Trader) sources
(chartinglens.com, theinnercircletraders.com, completetradersedge.com --
surfaced via a Google AI-overview synthesis after `web_search` returned no
results; `browser_exec` fallback used): after a strong impulsive
"displacement" move, price retraces into the 62%-79% Fibonacci retracement
band of that impulse leg (the "Optimal Trade Entry" zone, 70.5% as the
stated "sweet spot"), where institutional order flow is hypothesized to
concentrate. Displacement operationalized here as a swing-low-to-swing-
high move exceeding `displacement_atr_mult`×ATR. Entry on price
touching into the OTE zone while still closing above the 79%
invalidation level; stop at that level; target the swing high. First ICT
Optimal Trade Entry strategy in this repo (0 prior KB hits).

## Strategy file

`strategies/2026-09-24_ict_optimal_trade_entry.py`

## Preliminary scan + grid test summary (Step 6)

Preliminary scan across `displacement_atr_mult ∈ {1.5, 2.0, 2.5}` on
QQQ/BTC-USDT showed uniformly negative-to-near-zero full-sample Sharpe
(-0.51 to +0.01), and a follow-up sweep of `swing_window`/`max_hold_days`
on QQQ found no config exceeding Sharpe 0.5. The full grid confirmed this:

72 cells: `displacement_atr_mult ∈ {1.5, 2.0, 2.5}` × `swing_window ∈ {3,
5}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles,
2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | **0.083 (6/72) — decisively weak** |
| equity pass | 6/36 |
| crypto pass | **0/36 (zero)** |
| low-vol pass | 6/24 |
| mid-vol pass | 0/24 |
| high-vol pass | 0/24 |
| best cell | SPY low-vol, displacement_atr_mult=2.0/swing_window=3, Sharpe 2.22 |
| worst cell | BTC/USDT mid-vol, displacement_atr_mult=2.5/swing_window=5, Sharpe -1.03 |

Only 6 cells pass, all in the equity low-vol regime; crypto fails
completely across every configuration (0/36).

## Decision

**Reject across all symbols and asset classes** — decisive, uniform
failure (crypto 0/36, equity concentrated in a single narrow slice with
no broader robustness). Full single-config validator suite skipped as
uninformative given this outcome. Logged so a future loop does not
re-test this exact displacement+62-79%-retracement construction without a
materially different displacement definition or entry trigger.
