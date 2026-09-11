# 2026-09-11 BB Upper-Band Breakout + MACD Bullish Confirm (QQQ only) — ACCEPTED (QQQ)

**Hypothesis:** Per QuantifiedStrategies.com's "MACD and Bollinger Bands
Strategy - Trading Rules, Setup, Backtest (78% Win Rate)"
(https://www.quantifiedstrategies.com/macd-and-bollinger-bands-strategy/,
visited 2026-09-11), source's own disclosed "Trend-Following Strategy"
rule: "A buy signal occurs when the price breaks above the upper Bollinger
Band, and the MACD line crosses above the signal line, indicating upward
momentum." Distinct from the prior repo BB+MACD variant (2026-09-06-154,
LOWER-band mean-reversion confirmation) -- this is the UPPER-band
breakout TREND-FOLLOWING mechanic. Exit on close crossing back below the
middle band, MACD crossing back below signal, or a max_hold_days
time-stop.

## Grid test (bb_window in [15,20,25] x bb_std in [1.5,2.0] x max_hold_days in [15,20,30], QQQ/SPY/BTC-ETH, 3 vol terciles, 2018-01-01..2026-09-01)

- total_cells: 216, passed_cells: 22, pass_fraction: 0.102
- by_asset_class: equity 22/108 passed, crypto 0/108 passed (decisive rejection on crypto)
- by_vol_regime: low 16/72, mid 6/72, high 0/72
- best_cell: bb_window=25, bb_std=1.5, max_hold_days=20, QQQ, low-vol, Sharpe=2.21
- Best average-Sharpe config across equity symbols/regimes: bb_window=25, bb_std=1.5, max_hold_days=20 (avg 0.89)

## Single-config validation (bb_window=25, bb_std=1.5, max_hold_days=20 -- grid's best avg config, full sample)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 1.051 | 0.557 | >= 1.0 | **QQQ pass, SPY fail** |
| Max Drawdown | 0.131 | 0.075 | <= 0.25 | PASS both |
| TC survival (10bps/trade, 54/66 trades/8yr) | 0.952 | 0.403 | >= 0.5 | **QQQ pass, SPY fail** |
| Walk-forward (4 splits) | 1.0 | 0.75 | >= 0.75 | PASS both (SPY exactly at threshold) |
| Parameter sensitivity (18-cell grid rel-std) | 0.419 | 1.729 | <= 0.5 | **QQQ pass, SPY fail decisively** |

## Decision: ACCEPTED (QQQ only)

QQQ passes all 5 validators cleanly (Sharpe 1.05, MDD 0.13, TC-survival
0.95, WF 4/4, param-sens rel-std 0.42). SPY fails Sharpe, TC-survival, and
parameter sensitivity decisively (rel-std 1.73, more than 3x the 0.5
threshold -- SPY performance is highly fragile to the exact bb_window/
bb_std/max_hold_days choice at this config). Crypto (BTC/USDT, ETH/USDT)
is decisively rejected (0/108 grid cells). Scope explicitly limited to
QQQ; do NOT trade this on SPY or crypto. Strategy kept live in
strategies/ for QQQ use only.
