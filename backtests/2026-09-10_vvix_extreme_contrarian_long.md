# 2026-09-10 — VVIX Extreme-Spike Contrarian Long (REJECTED)

## Hypothesis

The CBOE VVIX Index (volatility of VIX) has a long-term mean near 86; per a
2026 VVIX trading guide, readings above 120 signal extreme fear-of-a-VIX-spike
but historically mark peak uncertainty rather than crash onset (reported
positive average 10-day forward SPX return ~+1.2% following VVIX>120
closes). Tested here as a contrarian long entry on SPY/QQQ when ^VVIX
closes above a threshold, exiting on mean-reversion back below a lower
threshold or a time-stop.

Strategy file: `strategies/2026-09-10_vvix_extreme_contrarian_long.py`
(equity-only — VVIX has no crypto analogue, so BTC/ETH were not tested).

## Single-config validator results (vvix_extreme=120, vvix_exit=100, max_hold_days=15)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass fraction | Trades |
|---|---|---|---|---|---|
| SPY | 0.458 (fail, thr 1.0) | 0.275 (fail, thr 0.25) | 0.418 (fail, thr 0.5) | 0.50 (fail, thr 0.75; 2/4) | 38 |
| QQQ | 0.556 (fail, thr 1.0) | 0.247 (pass, thr 0.25) | 0.522 (pass, thr 0.5) | 0.50 (fail, thr 0.75; 2/4) | 38 |

Parameter sweep (vvix_extreme in {110,130,140} x max_hold_days in
{10,20,30}, SPY): best full-sample Sharpe found was 0.716
(vvix_extreme=130, max_hold_days=30) — never reached the 1.0 threshold at
any tested combination.

## Step 6 grid summary (vvix_extreme x max_hold_days x QQQ/SPY x low/mid/high vol terciles)

- 72 cells, 22 passed (pass_fraction 0.306), equity only (no crypto
  analogue for VVIX).
- By vol regime: low 14/24, mid 1/24, high 7/24 -- some vol-regime-sliced
  cells pass (best cell Sharpe 1.999, vvix_extreme=130/max_hold=10, SPY
  low-vol), but this is thin-sample noise: full-sample (unsliced) Sharpe
  never crosses 1.0 for any parameter combination tested above, and
  walk-forward on the full sample fails decisively (2/4 splits positive,
  threshold requires 3/4).

## Decision: REJECT

Full-sample Sharpe fails the 1.0 threshold for every parameter combination
tried, and walk-forward robustness fails outright (only 2 of 4 splits
positive vs. 3-of-4 required) for both SPY and QQQ at the primary config.
The vol-regime-sliced grid passes are consistent with thin-sample overfitting
rather than a real edge. Not a near-miss worth revisiting without either
(a) a materially different exit rule, or (b) combining with an independent
confirming filter (e.g. VIX term-structure state) rather than VVIX level
alone.
