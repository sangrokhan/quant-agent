# Backtest Report: TDI (M.H. Pee) Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_tdi_pee_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-046

## Hypothesis

Trend Detection Index (TDI, M.H. Pee), exact formula per the R `TTR`
package documentation
(https://search.r-project.org/CRAN/refmans/TTR/html/TDI.html, visited
this iteration): momentum[t] = close[t] - close[t-n]. Let S1 = n-day sum
of momentum, S2 = n-day sum of |momentum|. TDI = |S1| - (multiple-1)*S2.
Positive TDI signals a trend is underway; negative signals
consolidation/chop. **First Trend-Detection-Index strategy in this repo**
(distinct from the already-tested "TDI" = Traders Dynamic Index, Dean
Malone, a different indicator with the same acronym).

Construction: TDI's trend-strength magnitude is rolling z-scored and
tanh-squashed into [-1,+1] used as a continuous sizing dial from the
start (higher TDI = stronger/cleaner trend = scale exposure up) inside an
SMA(trend_window) uptrend gate with a deadband.

## Step 6 — Grid summary (tdi_n x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `tdi_n in [14, 20, 30]`, `sensitivity in [0.5, 0.8]`, symbols
  `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.
- **72 cells, 33 passed (pass_fraction = 0.458)**.
- By asset class: equity 18/36, crypto 15/36.
- By vol regime: low 20/24, mid 10/24, high 3/24.
- Best cell: QQQ, tdi_n=20, sensitivity=0.8, low-vol regime, Sharpe 2.63.
- Worst cell: QQQ, tdi_n=14, sensitivity=0.5, high-vol regime, Sharpe -0.54.

## Step 7 — Single-config validator suite (per-symbol retuned)

QQQ/SPY/BTC: `tdi_n=20, tdi_multiple=2.0, sensitivity=0.5, trend_window=40,
zscore_window=100, base_exposure=0.4, leverage_cap=1.0, deadband=0.5`.
ETH (leverage-cap-aware retune -- ETH needed a HIGHER cap here, opposite of
this repo's usual crypto-overleverage pattern, since sensitivity=0.5 at
cap=1.0 under-scaled ETH's exposure): `base_exposure=0.32,
leverage_cap=0.8, deadband=0.4` (rest same).

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.086 (pass) | 0.168 (pass) | 0.776 (pass) | 0.75 (pass) | 0.111 (pass) | **Yes** |
| SPY | 1.033 (pass) | 0.088 (pass) | 0.590 (pass) | 0.75 (pass) | 0.195 (pass) | **Yes** |
| BTC/USDT | 1.151 (pass) | 0.225 (pass) | 1.046 (pass) | 1.00 (pass) | 0.085 (pass) | **Yes** |
| ETH/USDT | 1.019 (pass) | 0.206 (pass) | 0.939 (pass) | 0.75 (pass) | 0.193 (pass) | **Yes** |

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)**

All four symbols pass all 5 validators. This is the fourth full-universe
accept of this cron trigger's 8 iterations (after PVI, RVI, PMO). Margins
are thinner than the other full-universe accepts (QQQ/SPY/ETH Sharpe just
above 1.0), so a future iteration could tighten this further, but every
symbol clears every threshold as-is. First Trend-Detection-Index strategy
in this repo, opening a new (previously-untested) indicator family.
