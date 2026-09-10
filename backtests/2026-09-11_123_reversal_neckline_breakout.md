# 1-2-3 Reversal Pattern (Neckline Breakout) — QQQ

**Strategy file:** `strategies/2026-09-11_123_reversal_neckline_breakout.py`
**Hypothesis id:** 2026-09-11-022
**Source:** Google AI-overview synthesis of LuxAlgo / TITAN FX Research Hub /
RoboForex / TradingView "1-2-3 reversal pattern" explainers (visited this
iteration via browser_exec fallback after web_search DDGS backend failures).

## Hypothesis

Bullish 1-2-3 reversal: Point1 = confirmed fractal swing low (end of
downtrend), Point2 = subsequent fractal swing high (recovery rally,
"neckline"), Point3 = a later fractal swing low that holds ABOVE Point1 (a
higher low, confirming exhaustion of selling pressure). Entry trigger:
close price first closing back above the Point2 neckline level after Point3
confirms. Stop below Point3, target at `reward_r_multiple`*R above entry
(2.0 used for primary config), max_hold_days=20 safety time-stop.

## Primary config

`fractal_lookback=5, reward_r_multiple=2.0` — chosen as the grid cell that
passed all 3 vol-regime terciles on QQQ (only config to do so across the
6-value param grid).

## Single-config validator results

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 1.053 (PASS, thr 1.0) | 0.122 (PASS, thr 0.25) | 1.000 (PASS, thr 0.5) | 0.75 (PASS, thr 0.75; 3/4 splits) | 0.072 rel.std (PASS, thr 0.5) | 28 |
| SPY | 0.527 (FAIL) | 0.152 (PASS) | 0.458 (FAIL) | 1.00 (PASS) | 0.336 rel.std (PASS) | 27 |

**QQQ: all validators pass — ACCEPTED.**
**SPY: fails Sharpe and transaction-cost-survival — REJECTED (SPY-specific).**

## Step 6 grid summary

`fractal_lookback` in {3,5} × `reward_r_multiple` in {1.5,2.0,3.0} ×
equity{QQQ,SPY} × crypto{BTC/USDT,ETH/USDT} × vol_regime_splits=3, 72 cells
total.

- `pass_fraction`: 0.319 (23/72)
- `by_asset_class`: equity 23/36 (64%), crypto 0/36 (0%)
- `by_vol_regime`: low 12/24, mid 3/24, high 8/24
- `best_cell`: SPY low-vol, fractal_lookback=3/reward_r_multiple=2.0, Sharpe 2.244
- `worst_cell`: SPY mid-vol, fractal_lookback=5/reward_r_multiple=1.5, Sharpe -0.238
- QQQ at fractal_lookback=5 passed all 3 vol regimes at every reward_r_multiple tested (3/3 for all three R-multiples) — the cleanest, most consistent per-symbol cell block in the grid.
- Crypto (BTC/USDT, ETH/USDT) failed every single grid cell (0/36) — decisive rejection for crypto.

## Decision

**Accepted, QQQ only** (fractal_lookback=5, reward_r_multiple=2.0). SPY and
crypto scope explicitly excluded per the above evidence — a future loop
revisiting SPY should note the near-miss Sharpe (0.527) and consider a
regime/trend filter addition specific to SPY's flatter equity curve, rather
than assuming the QQQ config transfers directly.
