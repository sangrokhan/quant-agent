# Backtest report: ADXR trend-strength threshold-crossing confirmation

**Strategy file:** `strategies/2026-09-07_adxr_trend_strength_threshold.py` (kept as rejected-attempt record)
**Outcome:** REJECTED — decisive full-sample Sharpe fail on both QQQ and SPY.

## Hypothesis

Per forex-indicators.net's ADXR page: ADXR is a smoothed "rating" of ADX
(average of ADX now and ADX `adxr_lag` periods ago), reacting more slowly to
short-term reversals than raw ADX. Source rule: "When ADXR is above 25, use
a trend-following system... a rising ADXR with +DI above -DI indicates a
strengthening bullish market." Operationalized as a threshold-CROSSING entry
(ADXR crosses up through 25, confirmed by +DI>-DI at entry), distinct from
the already-rejected plain ADX/DMI directional-crossover strategy
(2026-09-03-017) which triggers on the DI crossover itself gated by raw ADX
magnitude, not a smoothed rating crossing a fixed threshold.

## Grid test summary (Step 6)

`param_grid={"adxr_threshold": [20,25,30], "adx_window": [10,14,21]}`,
`symbols={"equity": [QQQ, SPY], "crypto": [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, period 2019-01-01 to 2026-09-01 (108 cells).

- **pass_fraction: 0.083** (9/108 cells)
- **by_asset_class:** equity 9/54 passed; crypto **0/54** (decisive reject)
- **by_vol_regime:** low 7/36; mid 2/36; high **0/36** — only works, barely, in low-vol regimes; fails completely in high-vol
- **best_cell:** adxr_threshold=25, adx_window=10, SPY, low-vol, Sharpe 2.22
- **worst_cell:** adxr_threshold=30, adx_window=10, SPY, high-vol, Sharpe -1.61

## Single-config validation (Step 7) — best grid config (adxr_threshold=25, adx_window=10), full sample

| Symbol | Sharpe (thr 1.0) | Max DD (thr 0.25) |
|---|---|---|
| QQQ | -0.123 FAIL | 0.196 PASS |
| SPY | 0.389 FAIL | 0.082 PASS |

Full-sample Sharpe is decisively negative/near-zero on both symbols despite
the low-vol-regime "best cell" looking attractive (Sharpe 2.22) — same
pattern seen repeatedly this repo (BB/Keltner/APZ/ADXR): the headline grid
best-cell result comes entirely from a narrow low-vol slice and does not
generalize. Walk-forward/parameter-sensitivity skipped given the decisive
full-sample Sharpe fail (negative for QQQ) already settles the outcome.

## Conclusion

**Rejected.** Fourth strategy in a row in this repo's history to show the
same "only works in a cherry-picked low-vol regime slice, fails on full
sample and on crypto" pattern (after BB meanrev, Keltner breakout, APZ, now
ADXR trend-strength). This is a strong enough recurring signal that future
loops should treat "grid pass_fraction driven almost entirely by the
low-vol tercile" as a yellow flag worth checking full-sample Sharpe
*before* spending further validator budget, rather than as a promising lead
to chase into Step 7.
