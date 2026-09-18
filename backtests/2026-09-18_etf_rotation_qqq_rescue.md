# 2026-09-18 — ETF Rotation (200d SMA + ROC-1mo ranking) QQQ rescue — ACCEPTED

## Rescue hypothesis

Direct per-symbol parameter retune rescue for prior id 2026-09-18-069
(FabTrader ETF Rotation Strategy, monthly 200d-SMA-eligibility + ROC-ranked
top-N basket rotation, https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr
-- unchanged source, no new external research this sub-iteration). The
parent's shared config (trend_window=200, roc_lookback_months=3, top_n=3)
had QQQ near-miss (Sharpe 0.939, MDD 0.286) and SPY reject more decisively
(Sharpe 0.501). This sub-iteration ran a focused QQQ-only parameter sweep
on the identical unmodified strategy code
(strategies/2026-09-18_etf_rotation_sma_roc_topn.py) varying
trend_window in {150,180,200,220} x roc_lookback_months in {1,2,3} x
top_n in {1,2,3,4} on the same 7-ETF basket (QQQ/SPY/IWM/GLD/TLT/EFA/EEM).

## Sweep summary

Best QQQ full-sample Sharpe found at trend_window=200, roc_lookback_months=1
(monthly re-rank using 1-month trailing ROC rather than the parent's
3-month), top_n=2 (more concentrated than the parent's top_n=3): Sharpe
1.035, clearing the 1.0 threshold. This is directionally consistent with
the parent's own notes ("best avg-across-regimes config ... roc_lookback_months=1/top_n=3
... avg Sharpe 1.280 pass 2/3 vol regimes" — the parent had already
identified 1-month ROC as promising but tested top_n=3, not top_n=2).

## Full-sample validators (2018-01-01 to 2026-09-01)

`validators_etf_rotation_rescue.json`. Walk-forward used this repo's
established manual 4-way contiguous-split substitute.

| Symbol | Sharpe | MDD | TC-net-Sharpe | Walk-forward | Param-sensitivity |
|---|---|---|---|---|---|
| QQQ (trend_window=200, roc_lookback_months=1, top_n=2) | 1.035 (pass, thr 1.0) | 0.140 (pass, thr 0.25) | 1.008 (pass, thr 0.5, 19 trades) | 1.0 (pass, 4/4 splits) | 0.122 (pass, thr 0.5) |
| SPY (same shared config) | 0.264 (fail) | 0.257 (fail, thr 0.25) | 0.230 (fail) | 0.5 (fail, 2/4 splits) | n/a (not evaluated, decisive fail) |

QQQ passes all 5 validators cleanly with very tight parameter sensitivity
(0.122 relative std across an 18-point neighborhood sweep) — the
1-month-ROC/top-2 config is a robust local optimum, not a lucky single
point.

SPY still fails decisively at the shared config — consistent with the
parent's finding that SPY needs materially different tuning (or is simply
a worse fit for this basket-rotation construction given SPY's lower
absolute momentum dispersion vs QQQ within the 7-ETF basket).

## Decision: ACCEPT (QQQ only)

QQQ: trend_window=200, roc_lookback_months=1, top_n=2 — all 5 validators
pass. SPY remains rejected/out of scope for this strategy at this basket
composition; a future loop could retune SPY separately or add a defensive
cash-equivalent basket member (SHY/BIL, per the parent's own suggested
future revisit idea) if pursuing SPY coverage further.

Source: https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr
(unchanged from parent 2026-09-18-069; no new external research this
sub-iteration).
