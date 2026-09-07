# ASI Swing-Channel Breakout + Low-Vol Regime Gate — Backtest Report

**Date:** 2026-09-07 | **Strategy file:** `strategies/2026-09-08_asi_swing_channel_volgate.py`

## Hypothesis

Direct follow-up to near-miss 2026-09-08-026 (ASI swing-channel
breakout, full-sample Sharpe 0.734 SPY / 0.949 QQQ, MDD/TC/WF all pass;
grid strongly concentrated in low-vol: 12/24 low vs 4/24 mid vs 0/24
high). Adds a realized-vol regime gate (20d vol <= trailing 1yr median,
same construction as the accepted BB mean-reversion strategy) restricting
entries to the low-vol regime only, keeping ASI-channel entry/exit logic
unchanged otherwise.

## Step 6 — Grid summary (6 param combos x 4 symbols x 3 vol regimes = 72 cells)

- **Overall pass_fraction: 12/72 (16.7%)** — concentrated entirely in low-vol equity as intended
- By asset class: equity 12/36, crypto 0/36
- By vol regime: low 12/24 (50%), mid 0/24, high 0/24 (gate successfully removed mid/high losses)
- Best cell: QQQ low-vol, channel_window=30/max_hold=20, Sharpe 2.57
- Worst cell: SPY high-vol (residual cell), Sharpe -1.19

## Step 7 — Single-config validation (channel_window=30/max_hold=20, QQQ & SPY)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.781 ❌ | 0.843 ❌ | ≥ 1.0 |
| Max drawdown | 0.191 ✅ | 0.125 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | net Sharpe 0.720 ✅ | net Sharpe 0.752 ✅ | ≥ 0.5 |
| Walk-forward (manual 4-quarter fallback) | 3/4 splits ✅ | 4/4 splits ✅ | ≥ 75% |
| Parameter sensitivity | rel_std 0.291 ✅ | rel_std 0.449 ✅ | ≤ 0.5 |

SPY improved meaningfully (Sharpe 0.734 → 0.843) and now passes every
other validator cleanly. QQQ's Sharpe actually declined slightly (0.949
→ 0.781) since gating removed some winning mid-vol trades that had
contributed to QQQ's original near-miss. Both symbols are STILL
near-misses on Sharpe alone -- closer than the ungated base on SPY, but
neither clears 1.0.

## Step 8 — Decision: **REJECTED (persistent near-miss)**

Every other validator (MDD, TC-survival, walk-forward, parameter
sensitivity) passes cleanly on both QQQ and SPY -- this remains a
structurally sound, low-risk strategy, just short on risk-adjusted
return. The low-vol gate helped SPY meaningfully but not enough, and
modestly hurt QQQ by removing some of its mid-vol winning trades. Unlike
the VQI and Garman-Klass regime-gate attempts earlier this session, this
one had by far the cleanest regime-concentration signature going in, yet
STILL didn't clear the Sharpe bar -- suggesting the base edge here is
simply too weak overall (rather than merely diluted by a wrong regime),
and further parameter/regime tweaking is unlikely to be productive
without a more fundamental construction change.
