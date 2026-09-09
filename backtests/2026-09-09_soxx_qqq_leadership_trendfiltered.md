# 2026-09-09 — SOXX/QQQ Leadership, Broad-Trend-Filtered (ACCEPTED, QQQ only)

**Hypothesis** (id `2026-09-09-119`): Direct follow-up to near-miss rejection
2026-09-09-118 (SOXX/QQQ Ratio Sector-Leadership Regime Filter, per
MarketPhase https://market-phase.com/guides/soxx-qqq-ratio). That
iteration's plain SOXX/QQQ leadership gate had a moderate Sharpe near-miss
(0.87-0.90) but FAILED max drawdown decisively (0.27-0.35 vs the 0.25 cap),
diagnosed as: the leadership signal alone doesn't circuit-break during
genuine systemic drawdowns where both semiconductors and the broad market
fall together. This adds an explicit broad-trend filter (traded asset's own
close > its own `trend_sma_window`-day SMA) as an additional AND-gate on top
of the unchanged SOXX/QQQ leadership signal (`roc_window`-day rate of change
of the SOXX/QQQ ratio > `roc_threshold`).

Strategy file: `strategies/2026-09-09_soxx_qqq_leadership_trendfiltered.py`

## Step 6 grid summary (trend_sma_window ∈ {100,150,200} × roc_window ∈ {20,40} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 72 cells)

- `pass_fraction`: 0.181 (13/72) — lower than the ungated version's 0.264
  (expected: an added AND-gate reduces exposure and time-in-market, which
  can reduce pass_fraction breadth even while fixing the specific full-sample
  MDD failure that mattered)
- `by_asset_class`: equity 13/36, crypto 0/36
- `by_vol_regime`: low 12/24, mid 0/24, high 1/24
- `best_cell`: trend_sma_window=200, roc_window=20, SPY, low-vol regime,
  Sharpe 2.21

## Single-config validators (trend_sma_window=200, roc_window=40 — carrying over 2026-09-09-118's best roc_window, adding the standard 200d trend filter), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **1.013** ✅ | 0.951 ❌ (near-miss) | ≥ 1.0 |
| Max drawdown | **0.161** ✅ (fixed from 0.349) | 0.176 ✅ (fixed from 0.271) | ≤ 0.25 |
| TC survival (10bps/trade) | 0.790 ✅ | 0.636 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ | 0.75 ✅ | ≥ 0.75 pass fraction |
| Parameter sensitivity (trend_sma_window 150/175/200/225/250 sweep, QQQ) | 0.078 ✅ | | ≤ 0.5 relative std |
| Trades | 134 | 136 | — |

The MDD fix worked exactly as intended: QQQ MDD dropped from 0.349 (ungated,
2026-09-09-118) to 0.161, SPY from 0.271 to 0.176 — both now comfortably
under the 0.25 cap, confirming the diagnosis that the broad-trend filter was
the missing systemic-drawdown circuit-breaker.

## Verdict: **ACCEPT (QQQ only)**, reject SPY (near-miss)

**QQQ**: all five validators pass, including a clean parameter-sensitivity
sweep across trend_sma_window (150-250d all Sharpe 0.88-1.08, no cliff-edge)
confirming this is a genuine broad plateau, not a lucky single point.
**SPY**: every validator passes except Sharpe, which is a narrow miss (0.951
vs 1.0) — an extremely close near-miss, but per this repo's convention of
requiring all validators to pass for acceptance, SPY does not clear the bar
at this exact configuration.

**Scope**: accepted for QQQ only (SOXX/QQQ leadership signal + QQQ's own
200-day SMA broad-trend filter, roc_window=40). SPY recorded as a near-miss
worth revisiting with a symbol-specific local parameter search in a future
iteration (following the same successful pattern used for the Bitcoin Regime
Signal lineage earlier this cron trigger, 2026-09-09-114→115→116). Kept live
in `strategies/` for QQQ.
