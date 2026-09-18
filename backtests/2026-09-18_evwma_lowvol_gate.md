# 2026-09-18-076: eVWMA Price Crossover + Low-Volatility Regime Gate (Rescue Attempt)

## Hypothesis

Direct fix attempt for 2026-09-18-075 (eVWMA price crossover, consistent
Sharpe near-miss across all 4 symbols). -075's grid data showed the edge
concentrated in low-vol regimes (18/24 pass low-vol vs 0/24 high-vol) and
crypto failed MDD decisively. This iteration adds an explicit
volatility-regime gate (this repo's established pattern): trade the
identical eVWMA crossover ONLY when 20-day realized vol is at/below its
trailing 1-year median.

Source: same as 2026-09-18-075.

## Single-config validation (vol_lookback=40, max_hold_days=15,
vol_regime_window=20, vol_regime_lookback=252, vol_regime_ratio=1.0,
2018-01-01..2026-09-01)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|---|---|
| Sharpe ratio | 0.468 (**fail**) | 0.423 (**fail**) | 0.473 (**fail**) | 1.228 (pass) | 1.0 |
| Max drawdown | 0.163 (pass) | 0.154 (pass) | 0.423 (**fail**) | 0.559 (**fail**) | 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.223 (**fail**) | 0.093 (**fail**) | 0.369 (**fail**) | 1.136 (pass) | 0.5 |
| Walk-forward (4 splits, manual substitute) | 1.00 (pass) | 1.00 (pass) | 0.75 (pass) | 1.00 (pass) | 0.75 |

## Decision

**Rejected -- rescue backfired for equity, only partially helped ETH.**
The volatility-regime gate made QQQ and SPY dramatically WORSE (Sharpe
dropped from 0.969/0.991 to 0.468/0.423, transaction-cost survival
collapsed to 0.223/0.093) rather than better -- gating out high-vol periods
apparently removed some of the strategy's BEST trades (high-volume,
high-volatility breakout events are exactly where eVWMA's participation-
adaptive fast-tracking should shine, per the source's own design rationale
-- excluding high-vol regimes cuts against the indicator's core strength).
BTC/USDT still fails Sharpe, MDD, and TC-survival despite the gate.

ETH/USDT is the sole partial success (Sharpe 1.228, TC-survival 1.136,
walk-forward 1.0) but still fails MDD decisively (0.559 vs 0.25) -- not
an accept.

This confirms -075's own hypothesis about high-vol regimes was directionally
correct for identifying WHERE the risk lives, but the naive "just exclude
high-vol entirely" gate removes value along with risk for equity assets.
The eVWMA strategy line is now considered exhausted for this repo without
a more surgical fix (e.g. an MDD-triggered de-risking overlay instead of a
blanket vol-regime exclusion, or an asymmetric approach that keeps trading
through high-vol but tightens stops, similar to the Radge Weekend Trend
Trader's asymmetric-trail-stop design tested earlier this cron trigger).
