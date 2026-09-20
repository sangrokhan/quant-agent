# Backtest Report: 52-Week High Proximity + Trend Stack + ATR Consolidation + Bounce Trigger

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_52wk_high_proximity_consolidation_bounce.py`
**Source:** https://easyswing.trading/blog/52-week-high-pullback-swing-trading (visited via `browser_exec`; `web_search` failed all queries this iteration with a DDGS/rustls TLS-EOF backend error)

## Hypothesis

Per George & Hwang (2004, *Journal of Finance*) and EasySwing.trading's disclosed
"52-Week High Pullback" implementation: stocks near their 52-week high, in a
confirmed intermediate uptrend, pausing in a low-range consolidation, then
bouncing off that pause continue outperforming (anchoring-bias
under-reaction). The source's own strategy requires a cross-sectional
RS-rank>=80 gate versus a tracked universe, which this repo's single-symbol
`generate_returns_fn` architecture cannot compute — this adaptation drops
that gate and keeps six single-symbol-computable gates (trend stack,
SMA50 rising, proximity to 252d high, proximity improving vs 20d ago,
ADX floor, ATR-relative consolidation), triggered by a bounce candle, with
an ATR chandelier trailing stop replacing the source's fixed-ATR initial
stop + profit-target ladder (not expressible in this repo's
return-series-only contract).

## Grid Test Summary (Step 6)

`param_grid={"near_high_pct": [0.05,0.07,0.10], "adx_floor": [15,20],
"stop_atr_mult": [2.0,2.26,3.0]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, 2018-01-01 to
2026-09-01.

- **Total cells:** 216, **passed:** 70, **pass_fraction:** 0.324
- **By asset class:** equity 51/108 (0.472), crypto 19/108 (0.176)
- **By vol regime:** low 36/72 (0.50), mid 28/72 (0.389), high 6/72 (0.083)
- **Best cell:** equity/SPY, low-vol, `near_high_pct=0.05, adx_floor=15,
  stop_atr_mult=3.0`, Sharpe 2.36
- **Worst cell:** equity/SPY, mid-vol, `near_high_pct=0.05, adx_floor=20,
  stop_atr_mult=3.0`, Sharpe -1.47
- Best full-sample-averaged param combo across equity+crypto:
  `near_high_pct=0.07, adx_floor=15, stop_atr_mult=3.0` (avg Sharpe 0.654
  across QQQ/SPY/BTC/ETH low/mid/high slices; 0.716 equity-only)

The strategy holds up well **only in low-volatility regimes** (pass
fraction 0.50 vs 0.083 in high-vol) — a fresh 52-week-high consolidation
carries much weaker signal once realized vol has spiked (chased breakouts
rather than genuine pauses).

## Single-Config Validation (Step 7) — `near_high_pct=0.07, adx_floor=15.0, stop_atr_mult=3.0`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity (rel. std) |
|---|---|---|---|---|---|
| QQQ | 0.804 (FAIL, thr 1.0) | 0.159 (PASS) | 0.749 (PASS) | 1.00 (PASS) | 0.082 (PASS) |
| SPY | 0.787 (FAIL, thr 1.0) | 0.091 (PASS) | 0.700 (PASS) | 1.00 (PASS) | 0.428 (PASS) |
| BTC/USDT | 0.876 (FAIL, thr 1.0) | 0.348 (FAIL, thr 0.25) | 0.866 (PASS) | 1.00 (PASS) | 0.053 (PASS) |

Walk-forward used a manual 4-way contiguous split (`validators.check_walk_forward`
still errors on the installed vectorbt version — `vbt.utils.splitting`
missing, a known repo-wide issue, see `scratch_results/pjk_channel_validate.py`).

## Decision (Step 8): **REJECTED**

Full-period Sharpe (0.79–0.88 across all three symbols tested) falls short
of the 1.0 acceptance threshold everywhere, despite passing every other
validator (drawdown on equity, transaction costs, walk-forward, parameter
sensitivity) and despite a genuinely strong grid showing in low-vol regime
cells specifically (Sharpe up to 2.36). This is a **consistent, honest
near-miss** rather than a fluke — the grid's own `by_vol_regime` breakdown
shows the edge concentrates almost entirely in low-vol slices and mostly
evaporates in mid/high-vol, dragging the full-sample (all-regime) Sharpe
below threshold. BTC additionally fails max-drawdown outright (0.348 vs
0.25 threshold).

**Worth revisiting**: gating entries to ONLY the low-vol realized-vol
tercile (an explicit regime filter, following this repo's own
`2026-09-03_bb_meanrev_qqq_volregime.py` pattern) could plausibly push the
full-sample Sharpe over 1.0 on QQQ/SPY, since the underlying signal is
strong there — a future iteration could test that composite directly
rather than the always-on version tested here.
