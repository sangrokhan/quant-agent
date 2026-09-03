# Backtest Report: Gap-Down Fade (Intraday, Long-Only)

**Strategy file:** `strategies/2026-09-03_gap_down_fade.py`
**Date:** 2026-09-03
**Hypothesis id:** 2026-09-03-010

## Hypothesis

Source: https://daytradingtoolkit.com/strategies/gap-fill-gap-fade-strategy
-- academic literature (Berkman/Koch/Tuttle/Zhang 2012; Aboody/Even-Tov/
Lehavy/Trueman 2018; Akbas/Boehmer/Jiang/Koch 2022) finds overnight gaps
driven by retail sentiment tend to reverse (fade) intraday once daytime
arbitrageurs trade against the overnight order-flow imbalance. Adapted the
daily-granularity-testable core of this finding (long-only, since the loop
convention is no shorting): buy at the open after a gap down beyond
`gap_threshold`, sell at that day's close, betting on a partial intraday
reversal upward.

## Step 6 — Grid test summary

Grid: `gap_threshold ∈ {0.5%, 1%, 2%}` × symbols `{QQQ,SPY}` (equity),
`{BTC/USDT,ETH/USDT}` (crypto) × 3 vol terciles. 36 cells, 2019-01-01 to
2026-09-01.

| Slice | Passed / Total |
|---|---|
| Overall | 3 / 36 (8.3%) |
| Equity | 3 / 18 (16.7%) |
| Crypto | 0 / 18 (0.0%) |
| Low-vol | 1 / 12 (8.3%) |
| Mid-vol | 2 / 12 (16.7%) |
| High-vol | 0 / 12 (0.0%) |

Best cell: `gap_threshold=1%`, SPY, mid-vol regime, Sharpe 1.55 (a narrow
slice). Worst cell: `gap_threshold=0.5%`, QQQ, high-vol regime, Sharpe -0.82.
Overall pass fraction (8.3%) is the weakest of the three strategies tested
this cron trigger.

## Step 7 — Single-config validation (best config: SPY, gap_threshold=1%, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.08 | ≥ 1.0 |
| Max drawdown | ✅ | 14.4% | ≤ 25% |
| Transaction cost survival (10bps/trade, 116 trades) | ❌ | net Sharpe -0.20 | ≥ 0.5 |
| Walk-forward (4 windows, manual fallback -- vectorbt API bug, see notes) | ✅ | 3/4 splits positive Sharpe (75%) | ≥ 75% |
| Parameter sensitivity (3-point grid on SPY) | ❌ | relative std 0.73 | ≤ 0.5 |

Same `check_walk_forward` vectorbt API bug (`vectorbt.utils.splitting` not
present in the installed version) worked around identically to the prior two
iterations.

## Decision: **REJECT**

Full-sample Sharpe (0.08) collapses almost to zero once averaged across all
regimes/periods -- the "best cell" Sharpe of 1.55 was a mid-vol-tercile-only
artifact, not representative. With 116 gap-down trigger days over the
sample, 10bps/trade round-trip costs push net Sharpe solidly negative
(-0.20), and the parameter sweep (0.5%/1%/2% thresholds) shows the edge is
highly unstable across nearby threshold choices (relative std 0.73, nearly
1.5x the 0.5 ceiling). Three of five validators fail outright. This is
consistent with the source's own framing that the *specific* studied edge
requires intraday microstructure detail (pre-market volume, opening-range
confirmation, attention/catalyst screening) that a same-day-OHLCV-only
daily-bar approximation cannot capture -- the daily-granularity proxy tested
here does not survive. Strategy file and this report kept as a record of a
rejected attempt (not live).
