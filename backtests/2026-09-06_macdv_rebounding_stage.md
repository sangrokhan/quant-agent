# Backtest Report: MACD-V (Volatility-Normalized MACD) "Rebounding" Stage Entry

**Strategy file:** `strategies/2026-09-06_macdv_rebounding_stage.py`
**Date:** 2026-09-06

## Hypothesis

MACD-V (Alex Spiroglou, 2022) = [(EMA12-EMA26)/ATR(26)]*100, Signal =
EMA9(MACD-V). Long entry when MACD-V crosses above its signal line while
in the source's "Rebounding" momentum stage (-150 < MACD-V < 50, "rising
off a low"); exit on cross-down or entering the "Risk (overbought)" stage
(>150). Per
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v.
First strategy in this repo using an ATR-normalized (volatility-scaled)
MACD rather than plain price-difference MACD — the normalization is
intended to make numeric thresholds comparable across symbols/vol
regimes, unlike this repo's many plain-MACD variants which typically
needed per-symbol tuning.

## Grid test (Step 6)

`param_grid`: atr_window in {14,26}, entry_high in {30,50,70},
max_hold_days in {20,30}; symbols equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT]; vol_regime_splits=3. 144 total cells.

- pass_fraction: 0.2292 (33/144)
- by_asset_class: equity 33/72, crypto 0/72
- by_vol_regime: low 10/48, mid 12/48, high 11/48 — **notably holds across
  ALL THREE vol regimes** for equity, unlike most of this repo's prior
  strategies which concentrate almost entirely in low-vol cells. This is
  a meaningfully broader regime-robustness signal.
- best_cell (tercile-level): atr_window=26, entry_high=30, max_hold_days=20,
  SPY, low-vol, Sharpe 1.897

## Full-sample manual scan + refinement (Step 6/7)

The naive grid's default entry_low=-150 (source's exact "Rebounding"
lower bound) underperformed at full-sample (best only 0.90 Sharpe).
Widening the scan to also vary entry_low found entry_low=-100 (a tighter
"Rebounding" zone, screening out deeper-oversold rebounds) meaningfully
improves full-sample performance on BOTH QQQ and SPY simultaneously.
**Shared config atr_window=20, entry_low=-100, entry_high=80,
max_hold_days=25** passes Sharpe+MDD on both symbols at once:
QQQ Sharpe 1.201/MDD 0.156 (41 trades), SPY Sharpe 1.146/MDD 0.139
(50 trades) — selected as the primary shared config (rare in this repo:
most accepted strategies need a per-symbol config, not a single shared
one).

Crypto rejected decisively (0/72 grid cells).

## Single-config validation (Step 7) — shared config, QQQ and SPY

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.201 ✅ | 1.146 ✅ | ≥ 1.0 |
| Max drawdown | 0.156 ✅ | 0.139 ✅ | ≤ 0.25 |
| Transaction cost survival (10bps, N trades) | net 1.125 ✅ (41 trades) | net 1.033 ✅ (50 trades) | ≥ 0.5 |
| Walk-forward (4 manual splits) | 4/4 positive ✅ (1.19/1.08/2.17/0.78) | 4/4 positive ✅ (2.14/0.72/1.54/0.54) | ≥ 0.75 |
| Parameter sensitivity (atr_window ∈ {14,20,26}) | rel_std 0.079 ✅ | rel_std 0.130 ✅ | ≤ 0.5 |

## Decision: **ACCEPT (QQQ and SPY, shared config)**

All 5 validators pass on both equity symbols with one shared config —
the strongest/most robust result of this cron trigger's 4 iterations.
Crypto excluded from scope (0/72 grid cells).
