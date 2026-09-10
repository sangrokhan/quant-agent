# HYG Absolute-Trend Credit-Spread Regime Gate — SPY

**Strategy file:** `strategies/2026-09-11_hyg_absolute_trend_regime_gate.py`
**Hypothesis id:** 2026-09-11-027
**Source:** Google AI-overview synthesis of the "HYG Absolute Trend Rules"
market timing model (visited this iteration).

## Hypothesis

HYG (high-yield corporate bond ETF) price above/below its own 200-day SMA
is a systemic credit-spread risk-on/risk-off regime gate. Applied here as a
gate on a primary asset's (QQQ/SPY) own SMA trend-following signal: long
only when both the primary asset is above its own trend SMA AND HYG is
above its own 200-day SMA.

## Primary config

`trend_sma_window=150, hyg_sma_window=200`

## Single-config validator results

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.899 (FAIL, thr 1.0) | 0.156 (PASS) | 0.852 (PASS) | 0.75 (PASS) | 0.154 rel.std (PASS) | 36 |
| SPY | 1.141 (PASS) | 0.132 (PASS) | 1.076 (PASS) | 0.75 (PASS) | 0.193 rel.std (PASS) | 34 |

**SPY: all validators pass — ACCEPTED.**
**QQQ: fails only Sharpe (0.899, near-miss just below the 1.0 threshold) — REJECTED (QQQ-specific).**

## Step 6 grid summary

`trend_sma_window` in {50,100,150} x `hyg_sma_window` in {100,150,200} x
equity{QQQ,SPY} x crypto{BTC/USDT,ETH/USDT} x vol_regime_splits=3, 108
cells total.

- `pass_fraction`: 0.167 (18/108)
- `by_asset_class`: equity 18/54 (33%), crypto 0/54 (0%)
- `by_vol_regime`: low 18/36 (all passes concentrated here), mid 0/36, high 0/36
- Every single param combo (9 combos x 2 symbols = 18 cells) passed EXACTLY the low-vol tercile and nothing else — a very consistent pattern suggesting the credit-spread-gate edge (if real) is concentrated in calm markets, not a broad-regime effect.
- Crypto (BTC/USDT, ETH/USDT) failed every single grid cell (0/54) — decisive rejection for crypto (expected, since HYG has no crypto analog).

## Decision

**Accepted, SPY only** (trend_sma_window=150, hyg_sma_window=200). QQQ
near-miss (0.899 Sharpe) is a candidate for a future loop's fine-tune
revisit. Crypto excluded as expected (no credit-market analog).
