# Backtest Report: Low-Volatility-Percentile Pullback (2026-09-26)

**Strategy file:** `strategies/2026-09-26_low_vol_percentile_pullback.py`
**KB id:** 2026-09-26-017

## Hypothesis

Per QuantifiedStrategies.com's FESX (EURO STOXX 50 futures) pullback
setup (disclosed via Facebook post, Google SERP snippet — the substack
article at the guessed URL 404'd): "ATR(14) is in the lowest 25% of the
past year" AND "Close below the 20-day MA" AND "Close above the 200-day
MA" triggers a long entry at "next open". Adapted here: ATR(14) below its
own trailing 252-day 25th percentile AND close<SMA(20) AND close>SMA(200),
entry at next bar's open; exit on close>SMA(20) or a max_hold_days
time-stop (source doesn't disclose an exit rule past "buy next open").
First strategy in this repo combining a volatility-PERCENTILE-COMPRESSION
filter with a short-term pullback nested inside a long-term uptrend.

## Grid test (Step 6)

`atr_percentile_threshold` in {0.15, 0.25, 0.35} x `short_ma_window` in
{10, 20, 30}, QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3, 2016-2026 (108 cells):

- pass_fraction = 0.139 (15/108)
- by_asset_class: equity 12/54, crypto 3/54
- by_vol_regime: low 9/36, mid 6/36, high 0/36
- best_cell: `atr_percentile_threshold=0.25, short_ma_window=10`, SPY,
  mid-vol, Sharpe 1.879
- worst_cell: `atr_percentile_threshold=0.15, short_ma_window=30`,
  ETH/USDT, low-vol, Sharpe -1.071

Full local 9-combo sweep found `atr_percentile_threshold=0.25,
short_ma_window=10` is the strongest region: QQQ full-sample Sharpe 0.771,
MDD 0.086; SPY full-sample Sharpe 1.258, MDD 0.058.

## Single-config validation (Step 7)

Config: `atr_percentile_threshold=0.25, short_ma_window=10, atr_window=14,
atr_percentile_lookback=252, long_ma_window=200, max_hold_days=20`, full
sample 2016-2026.

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 0.771 (**fail**, <1.0) | **1.258** (pass, ≥1.0) |
| Max Drawdown | 0.086 (pass, ≤0.25) | 0.058 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 0.665 (pass, ≥0.5) | 0.952 (pass, ≥0.5) |
| Walk-forward (manual 4-split) | 1.0 (pass, ≥0.75) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std, 9-cell) | 0.283 (pass, ≤0.5) | **0.708** (**fail**, >0.5) |
| num_trades | 36 | 54 |

## Decision

**REJECT (both symbols)**. QQQ fails on Sharpe alone (0.771, near-miss but
below 1.0). SPY has an attractive full-sample Sharpe (1.258, MDD only
5.8%) but fails parameter sensitivity decisively (rel. std 0.708 vs the
0.5 threshold) — the 9-cell local grid shows SPY's edge is highly
sensitive to the `atr_percentile_threshold` choice (Sharpe ranges from
0.096 at threshold=0.15/window=30 up to 1.258 at threshold=0.25/window=10),
meaning the attractive config is not robust to reasonable parameter
perturbation and would likely be overfit to this specific window choice.
Both symbols recorded as near-misses worth revisiting with a narrower,
more conservative parameter neighborhood in a future iteration (e.g.
threshold fixed near 0.20-0.30, window fixed near 8-12) to check if a
flatter, more robust region exists nearby.

## Source

Google SERP snippet of a QuantifiedStrategies.com Facebook post describing
the FESX pullback setup rule (substack URL guessed from the landing page
404'd; the rule itself was quoted verbatim in the search snippet) — read
via `browser_exec`.
