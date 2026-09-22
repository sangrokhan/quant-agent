# Backtest Report: ROC Oversold Mean-Reversion (Oscillating) + SMA Trend Filter

**Strategy file:** `strategies/2026-09-22_roc_oversold_meanrev.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-061

## Hypothesis

Per QuantifiedStrategies.com's "Price Rate of Change Strategy (ROC Indicator
- Trading Rules and Backtest, Performance)"
(https://www.quantifiedstrategies.com/rate-of-change-trading-strategy/, read
via browser_exec since web_extract's ddgs backend cannot fetch page bodies),
the article backtests 4 ROC variants on SPY and states the "oversold -
oscillating" mean-reversion variant was the best-performing of the 3 it
actually backtested (breakout and zero-line-cross variants "fall short",
divergence not backtested, "difficult to quantify"). Best reported lookback
settings were 4-6 days. This repo already tested plain zero-line-crossover
ROC (2026-09-11-092, accepted equity), so this iteration targets the
distinct oversold-oscillating variant: ROC dips below an oversold threshold
then recovers back above it (long entry), gated by an SMA(200) uptrend
filter per the source's own long-term-direction caveat.

## Grid Test Summary (Step 6)

- Total cells: 72 (3 roc_window x 2 oversold_level, 3 vol regimes, QQQ/SPY
  equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.042 (3/72)
- By asset class: equity 2/36, crypto 1/36
- By vol regime: low 0/24, mid 2/24, high 1/24
- Best cell: SPY, roc_window=8/oversold_level=6.0, high-vol regime, Sharpe 1.47
- Worst cell: QQQ, roc_window=8/oversold_level=10.0, high-vol regime, Sharpe -1.31

## Single-Config Validation (Step 7), SPY, roc_window=8/oversold_level=6.0/exit_level=2.0/trend_window=200/max_hold_days=15

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** | 0.845 | 1.0 |
| Max drawdown | true | 0.000 | 0.25 |
| Transaction cost survival (10bps/trade, 3 trades) | true | net Sharpe 0.744 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true | 4/4 splits positive | 0.75 |
| Parameter sensitivity (6-combo sweep) | **false** | relative std 1.590 | 0.5 |

Only 3 trades fired over the full 2019-2026 SPY sample at the best config --
extremely low signal frequency (the entry AND-gate of "was oversold in prior
window" + "recovering above threshold" + "uptrend" is rare). MDD=0.0 is an
artifact of this: so few trades occurred that none overlapped a drawdown
period, not genuine robustness.

## Outcome: REJECTED

2 of 5 validators fail: Sharpe ratio misses threshold (0.845 vs 1.0
required) and parameter sensitivity fails decisively (relative std 1.59,
more than 3x the 0.5 threshold) -- Sharpe swings from strongly negative to
positive across the 6 tested roc_window/oversold_level combos, consistent
with the grid's low 0.042 pass_fraction. The extremely low trade count (3
over 7+ years) also makes the passing metrics (MDD, TC-survival,
walk-forward) statistically unreliable rather than genuinely robust. This
corroborates the source's own framing: oversold-oscillating was their
*relatively best* of 3 backtested ROC variants, but the source itself never
claimed strong absolute performance, and the strict AND-gate implementation
here (source rules + this repo's standard SMA trend filter) suppresses
signal frequency too much to be tradable. A future iteration could try
loosening the entry gate (e.g. drop the "was_oversold within window" memory
requirement and trigger directly on ROC < -oversold_level without waiting
for recovery) or widen exit_level, but this specific formulation is
rejected.
