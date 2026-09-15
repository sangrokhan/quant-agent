# Backtest Report: ADTM (Dynamic Buying/Selling Power) Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_adtm_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-101

## Hypothesis

ADTM compares intraday buying vs selling momentum, anchored on today's
open relative to yesterday's open (structurally distinct from this
cron trigger's own BRAR/CR entries, which anchor on open/close/median).
Formula, confirmed via two independent sources (Google SERP synthesis of
Luo/Li/Liu 2021 AIMS Press paper and 10jqka.com.cn's formula-platform
snippet, both corroborating):

    DTM(t) = max(High(t)-Open(t), Open(t)-Open(t-1)) if Open(t)>Open(t-1) else 0
    DBM(t) = max(Open(t)-Low(t), Open(t-1)-Open(t))   if Open(t)<Open(t-1) else 0
    STM(N) = SUM(DTM, N); SBM(N) = SUM(DBM, N)
    ADTM = (STM-SBM)/STM if STM>SBM; (SBM-STM)/SBM if STM<SBM; else 0

Naturally bounded ~[-1,+1]. First ADTM strategy in this repo. This
iteration uses ADTM directly (already bounded, no z-score needed) as a
CONTINUOUS SIZING dial inside an SMA(trend_window) uptrend gate with
deadband, leverage-cap-aware for crypto from the start.

Source: https://www.aimspress.com/article/doi/10.3934/NAR.2021006 and
http://poi.10jqka.com.cn, both surfaced via Google SERP snippet synthesis
(browser_exec) this iteration — full page text was JS-gated/paywalled but
the SERP snippets themselves quoted the exact formula verbatim from both
sources, corroborating each other.

## Grid test summary (`grid_result_adtm_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3. 72 cells.
- `pass_fraction`: **0.500** (36/72)
- `by_asset_class`: equity 18/36 (0.500), crypto 18/36 (0.500) — perfectly
  balanced, first sizing-dial entry this trigger with equal equity/crypto
  pass rates.
- `by_vol_regime`: low 24/24 (1.00), mid 12/24 (0.50), high 0/24 (0.00) —
  most extreme high-vol degradation of this trigger's 5 entries (complete
  failure in high-vol tercile).
- best cell: QQQ, sensitivity=0.4/deadband=0.30, low-vol, Sharpe 2.80.
- worst cell: QQQ, sensitivity=0.6/deadband=0.30, high-vol, Sharpe -0.40.

## Single-config validation (`validators_adtm_sizing.json`)

Per-symbol retuned config, full 2019-01-01..2026-09-01 sample:

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd pass frac | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.138 | 0.131 | pass | 1.00 | pass | PASS |
| SPY | 1.155 | 0.064 | pass | 1.00 | pass | PASS |
| BTC/USDT | 1.477 | 0.134 | pass | 1.00 | pass | PASS |
| ETH/USDT | 1.259 | 0.132 | pass | 1.00 | pass | PASS |

All 5 validators pass on all 4 symbols on the first parameter attempt (no
near-misses needing a widened search this time).

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First ADTM
strategy tested in this repo.

Per-symbol params used:
- QQQ: trend_window=40, adtm_window=23, base_exposure=0.4, sensitivity=0.5,
  leverage_cap=1.0, deadband=0.15
- SPY: sensitivity=0.4, deadband=0.30 (else same)
- BTC/USDT: base_exposure=0.2, sensitivity=0.15, leverage_cap=0.5, deadband=0.15
- ETH/USDT: base_exposure=0.2, sensitivity=0.15, leverage_cap=0.5, deadband=0.25
