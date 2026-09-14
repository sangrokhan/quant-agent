# MACD-V Continuous Sizing Dial on SMA(40) Trend Gate

**Hypothesis:** MACD-V (Alex Spiroglou, 2022) = [(EMA12-EMA26)/ATR(26)]*100,
clipped to [-100,+100] and rescaled to [-1,+1] as a CONTINUOUS SIZING dial
(exposure = base_exposure + sensitivity*macdv_centered) inside an
SMA(40) uptrend gate, deadband=0.20 to control turnover, leverage_cap=1.0.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
(browser_exec Google SERP fallback — web_search returned unrelated generic
oscillator design content, not this specific page).

Repo has 2 prior MACD-V entries, both binary threshold/crossover rules on
the source's "Rebounding"/"Rallying" momentum-stage zones (2026-09-06-094
accepted equity-only; 2026-09-12-155 rejected, Sharpe near-miss + crypto
decisive reject). This is the first continuous-sizing-dial variant.

## Grid test (Step 6)

`param_grid={sensitivity:[0.4,0.6,0.8], macdv_cap:[100,150], trend_window:[40]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
72 total cells.

- pass_fraction: **0.431** (31/72)
- by_asset_class: equity 18/36, crypto 13/36
- by_vol_regime: low 22/24, mid 9/24, **high 0/24** (edge concentrated in
  low/mid vol, decisively fails in high-vol regime across both asset classes)
- best_cell: sensitivity=0.8, macdv_cap=100.0, trend_window=40, QQQ low-vol,
  Sharpe=2.843
- worst_cell: sensitivity=0.6, macdv_cap=150.0, QQQ high-vol, Sharpe=-0.717

## Primary config validation (sensitivity=0.8, macdv_cap=100.0, trend_window=40)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.081 (pass) | 0.175 (pass) | 0.690 (pass) | 0.75 (pass) | 0.022 (pass) | **ALL 5 PASS** |
| SPY | 0.881 (fail, <1.0) | 0.109 (pass) | 0.404 (fail, <0.5) | 0.75 (pass) | 0.030 (pass) | 2/5 fail |
| BTC/USDT | 0.197 (fail) | 0.415 (fail) | -0.051 (fail) | 1.00 (pass) | 0.040 (pass) | 3/5 fail, decisive |
| ETH/USDT | 0.195 (fail) | 0.467 (fail) | -0.045 (fail) | 1.00 (pass) | 0.066 (pass) | 3/5 fail, decisive |

Walk-forward used a manual 4-slice fallback (pre-existing repo-wide
`vbt.utils.splitting` AttributeError, documented in prior backtest reports).

Crypto's num_trades is extremely high (7719/7730) relative to equity (202/203),
suggesting on crypto's finer-granularity/higher-noise MACD-V churns through
the deadband far more often — a decisive rejection, consistent with several
other sizing-dial strategies this cron trigger that only clear the bar on
equities.

## Decision

**Accepted for QQQ only.** SPY is a near-miss (Sharpe 0.88, TC-survival
0.40) but does not clear both thresholds. Crypto (BTC/ETH) decisively
rejected on Sharpe/MDD/TC-survival. Strategy file kept in `strategies/` as
QQQ-only live; SPY/crypto documented as out of scope in notes so a future
loop doesn't over-trust it beyond QQQ.
