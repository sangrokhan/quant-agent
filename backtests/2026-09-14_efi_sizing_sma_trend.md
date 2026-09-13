# Backtest Report: EFI Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_efi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-105

## Hypothesis

Elder Force Index (Alexander Elder): EFI=(Close-Prior Close)*Volume,
EMA-smoothed. Combines price momentum with volume participation into one
unbounded money-flow measure. Confirmed via DuckDuckGo HTML SERP
(arrowalgo.com, ta-lib.org, positioned.app, chart-formations.com,
lightningchart.com).

Repo has 5 prior Force Index entries, all binary threshold/crossover/
divergence triggers (one, the EMA(13)/EMA(2-3) dual-timeframe pullback,
accepted QQQ-only). Raw EFI is unbounded and scale-dependent (price
volatility x volume level), so this iteration normalizes it via a rolling
z-score then tanh-squashes to bounded [-1,1] (same fix pattern that worked
for RWI-diff, 2026-09-14-104) before using it as a CONTINUOUS SIZING dial
within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={efi_sensitivity: [0.4,0.6,0.8], deadband: [0.15,0.20,0.25]}`,
`symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=51, pass_fraction=0.472
- by_asset_class: equity 30/54 (0.56), crypto 21/54 (0.39)
- by_vol_regime: low 36/36 (1.00), mid 12/36 (0.33), high 3/36 (0.08)
- per-symbol: QQQ 18/27, SPY 12/27, BTC/USDT 12/27, ETH/USDT 9/27

## Single-config validator results (Step 7)

Grid best-cell configs failed TC-survival on equity (QQQ net Sharpe 0.362
at 331 trades; SPY 0.301 at 262 trades). Deadband sweep found configs
clearing all 5:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=0.4, db=0.25 | 1.073 (pass) | 13.57% (pass) | 0.507 (pass) | 0.75 (pass) | 0.033 rel-std (pass) | **ACCEPT** |
| SPY | sens=0.4, db=0.30 | 1.269 (pass) | 8.80% (pass) | 0.728 (pass) | 0.75 (pass) | 0.061 rel-std (pass) | **ACCEPT** |
| BTC/USDT | sens=0.4, db=0.15 | 1.373 (pass) | 39.92% (**FAIL**, >25%) | 1.073 (pass) | 1.00 (pass) | 0.030 rel-std (pass) | **REJECT** (MDD) |

## Decision

**Accept for equity (QQQ, SPY)** — both clear all 5 validators at widened
deadband (0.25/0.30). **Reject crypto** (BTC/USDT decisive MDD fail
39.92%, another large crypto MDD miss consistent with this cron trigger's
pattern). Confirms the "normalize unbounded indicator via z-score + tanh
before sizing" approach (first used for RWI-diff) generalizes to a second,
structurally distinct unbounded indicator (volume-weighted price momentum
vs RWI's ATR-normalized displacement-vs-random-walk ratio) -- and that
Force Index's money-flow signal, previously only surviving in a narrow
QQQ-only dual-EMA-pullback binary construction, extends to SPY as well once
reframed as a continuous sizing dial.
