# Backtest Report: Ehlers Center of Gravity Oscillator, ADX-gated (2026-09-04)

**Strategy file:** `strategies/2026-09-04_cog_oscillator_adxgate.py`
**Knowledge base id:** 2026-09-04-124
**Outcome:** REJECTED

## Hypothesis

John Ehlers' Center of Gravity (CG) oscillator (Cybernetic Analysis, 2004):

```
CG_t = -sum_{i=0}^{N-1} (i+1) * Price[t-i] / sum_{i=0}^{N-1} Price[t-i]
```

A near-zero-lag "balance point" oscillator whose turning points lead price
turns. Entry: CG crosses above a 1-bar-delayed trigger line while CG is at
an oversold extreme, gated by ADX(14) < adx_threshold (source recommends
restricting cycle-oscillator signals to ranging/non-trending regimes).
Exit: CG crosses back below trigger, an overbought extreme, or a
max_hold_days time-stop.

Sources:
- https://www.forexdominion.com/center-of-gravity-cog.html
- https://github.com/lavs9/quantwave/blob/main/docs/guides/indicators/native/center_of_gravity_oscillator.md

## Grid test summary (cg_period in {8,10,14} x adx_threshold in {20,25,30} x max_hold_days=10, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- total_cells: 108, passed_cells: 6, pass_fraction: 0.0556
- by_asset_class: equity 6/54, crypto 0/54
- by_vol_regime: low 3/36, mid 1/36, high 2/36
- best_cell: SPY, cg_period=8, adx_threshold=30, low-vol, Sharpe=1.52

## Single-config validation (cg_period=8, adx_threshold=30, max_hold_days=10)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.244 (FAIL) | 0.598 (FAIL) | >= 1.0 |
| Max drawdown | 0.341 (FAIL) | 0.216 (PASS) | <= 0.25 |
| TC survival (net Sharpe) | -0.009 (FAIL) | 0.186 (FAIL) | >= 0.5 |
| Walk-forward (4 splits) | 0.75 (PASS) | 0.75 (PASS) | >= 0.75 |
| Parameter sensitivity (rel std) | 0.440 (PASS) | 0.306 (PASS) | <= 0.5 |

## Verdict

Rejected. The best grid config only clears thresholds in narrow low-vol
slices; full-sample Sharpe/MDD/TC-survival fail decisively for both QQQ and
SPY (high trade count ~200-210 over 7.7yr causes heavy cost drag from
whipsaw at ADX regime boundaries). Crypto fails all 54 cells outright.
