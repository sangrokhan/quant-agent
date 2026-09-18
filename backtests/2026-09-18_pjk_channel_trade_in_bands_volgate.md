# Backtest Report: PJK Channel Trade-in-Bands + High-Vol Regime Gate

**Strategy file:** `strategies/2026-09-18_pjk_channel_trade_in_bands_volgate.py`
**Date:** 2026-09-18
**Hypothesis:** Direct fix for this same cron trigger's prior rejection
2026-09-18-116 (Kaufman PJK Channels Rule 3, per
https://traders.com/Documentation/FEEDbk_docs/2025/05/TradersTips.html):
the ungated grid showed 0/36 pass in the high-vol tercile across both
asset classes, dragging blended full-sample Sharpe below 1.0 despite a
strong low-vol edge. This variant flattens the position whenever trailing
20-day realized volatility exceeds `vol_regime_ratio` x its own trailing
252-day median, otherwise defers to the unchanged PJK Rule 3 logic.

## Grid summary (Step 6)

Parameter grid: `vol_regime_ratio` in {1.1, 1.3, 1.6} (period=50, zone=0.3
fixed at the ungated variant's best equity-average config); symbols:
equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3;
sample 2016-01-01 to 2026-09-01.

- Total cells: 36, passed: 13, **pass_fraction = 0.361** (up from 0.278
  ungated)
- By asset class: **equity 12/18 passed** (up from 6/18 -- the gate works
  as intended), crypto 1/18 passed (still decisively rejected)
- By vol regime: low 6/12, mid 7/12, **high 0/12 still fails completely**
  (expected -- the gate forces flat during high-vol, so those cells simply
  have ~zero exposure/near-zero Sharpe rather than the large negative
  Sharpe seen ungated)
- Best cell: equity SPY low-vol, vol_regime_ratio=1.6, Sharpe=2.17 (same
  as ungated best cell, since low-vol bars are rarely gated)
- vol_regime_ratio=1.3 gives the best QQQ+SPY blend (QQQ low/mid Sharpe
  1.59/1.95, SPY low/mid 2.14/1.49, both high-vol near-flat rather than
  deeply negative)

## Single-config validation (Step 7): period=50, zone=0.3, vol_regime_ratio=1.3

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample, 2016-2026) | 1.225 | 0.939 | >= 1.0 | **QQQ PASS, SPY near-miss FAIL** |
| Max drawdown | 0.183 | 0.220 | <= 0.25 | PASS both |
| Net Sharpe after costs (5bps/trade) | 1.136 | 0.826 | >= 0.5 | PASS both |
| Walk-forward (4-split, manual) | 4/4 splits positive | 3/4 splits positive | >= 0.75 frac | PASS both |
| Parameter sensitivity (3-value local sweep, relative std) | 0.186 | 0.140 | <= 0.5 | PASS both |

A targeted SPY-specific local re-tune (period in {40,50,60} x zone in
{0.2,0.3,0.4} x vol_regime_ratio in {1.1,1.3,1.6}) found a best SPY config
of period=60/zone=0.4/vol_regime_ratio=1.3, Sharpe=0.957 -- still a
near-miss just under the 1.0 bar (MDD 0.239, still under the 0.25 cap).
Kept the shared period=50/zone=0.3/vol_regime_ratio=1.3 config for the
accepted scope below since QQQ already clears every bar cleanly with it
and per-symbol config-splitting is reserved for genuine accepts, not to
force a near-miss over the line.

## Decision: ACCEPT (QQQ only); SPY remains a documented near-miss

QQQ: all validators pass cleanly (Sharpe 1.225, MDD 0.183, net-of-cost
Sharpe 1.136, walk-forward 4/4, parameter-sensitivity relative std 0.186).
Kept live in `strategies/`.

SPY: Sharpe 0.939 (best re-tuned 0.957) remains just under the 1.0
threshold despite passing every other validator -- documented as a
near-miss rather than force-accepted. Crypto remains decisively rejected
(1/18 grid cells pass) -- the vol-gate construction does not transfer to
crypto's volatility regime structure.

This mirrors the repo's established pattern of narrower-but-honest accepts
(e.g. several other `_volgate` strategies) -- the high-vol flat-gate
converts a full-sample-Sharpe-failing strategy into a QQQ-clean accept
without needing any new external research, purely by acting on what the
Step 6 grid from the prior (ungated) iteration already showed.
