# Traders Dynamic Index (TDI, Dean Malone) RSI/Signal/MBL Crossover — QQQ

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_tdi_rsi_signal_mbl_crossover.py`
**Source:** Google AI-overview synthesis (TrendSpider/fbs.com/TradeWill/Quantum Algo)

## Hypothesis

TDI (Dean Malone): RSI + fast SMA-of-RSI signal line + slow SMA-of-RSI
Market Base Line (MBL). Long entry when RSI was recently oversold (<32),
crosses above its own signal line (golden cross), confirmed by RSI/signal
being above MBL (uptrend filter). Exit on death cross or RSI > 68
(overbought).

## Grid test (Step 6)

`param_grid={"rsi_period": [9, 13, 21], "oversold_threshold": [25, 32, 40]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: **0.028 (3/108)** — extremely low
- By asset class: equity 3/54, crypto 0/54
- By vol regime: low 0/36, mid 1/36, high 2/36
- Best cell: rsi_period=9, oversold_threshold=32, QQQ, high-vol regime, Sharpe 1.05 (barely clears threshold)

## Single-config validation (Step 7) — rsi_period=9, oversold_threshold=32, QQQ full sample

- num_trades: 8 (extremely rare signal over 7.5 years)
- Sharpe: 0.574 (**FAIL**, threshold 1.0)
- Max drawdown: 0.031 (pass)
- Net-of-cost Sharpe: 0.517 (pass, barely — but moot given Sharpe fail)

## Decision: **REJECTED** (Sharpe fails decisively on full sample; the three-tier RSI/signal/MBL AND-gate combined with a recent-oversold lookback is too restrictive — only 8 trades over 7.5 years on QQQ, and the grid's best cell was a narrow high-vol-regime slice at exactly the pass threshold, not representative)

Crypto grid pass_fraction is 0/54 -- decisively rejected across the board.

Note for future loops: TDI's disclosed rule set is more naturally a
discretionary multi-confirmation system (candle-close timing, band context)
than a clean systematic signal; a future revisit could try a looser
single-condition variant (e.g. just the RSI/signal golden cross without the
oversold-lookback AND-gate) but this exact three-tier construction should
not be re-tried as-is.
