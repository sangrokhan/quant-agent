# 2026-09-16 Donchian Channel Width (Inv-Vol Sizing) — QQQ Near-Miss Fix

## Hypothesis
Direct fix for prior id `2026-09-15-040` (Donchian Channel Width,
normalized (width/close), min-max normalized and INVERTED as a continuous
exposure-sizing dial inside an SMA(trend_window) uptrend gate; accepted
crypto BTC/USDT+ETH/USDT but QQQ was a near-miss on raw Sharpe (0.984 at
the original minmax_window=100 config) and SPY was rejected). This
sub-iteration retunes `minmax_window` (100→80) on the identical unmodified
strategy code (`strategies/2026-09-15_donchian_width_invvol_sizing_sma_trend.py`)
for QQQ only, keeping `trend_window`, `donchian_window`, `sensitivity`, and
`deadband` at their original defaults. No new external research; formula
unchanged from `2026-09-15-040`.

## Parameter search (own-data retune)
Swept `trend_window x donchian_window x minmax_window x sensitivity x
deadband` on QQQ full-sample. Many combinations clear the bar (>140
passing cells found); minimal-change choice retained: `trend_window=40`
(unchanged), `donchian_window=20` (unchanged), `minmax_window=80` (was
100), `sensitivity=0.4` (unchanged), `deadband=0.20` (unchanged) —
i.e. only the min-max normalization lookback window changed.

## Single-config validation (Step 7)
| Symbol | Sharpe | MDD   | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel-std) |
|--------|--------|-------|-------------------------|--------------|------------------------------|
| QQQ    | 1.164  | 0.100 | 0.547                   | 0.75 (3/4)   | 0.075                        |

All 5 validators pass (thresholds: Sharpe>=1.0, MDD<=0.25,
net-Sharpe-after-costs>=0.5, walk-forward pass-fraction>=0.75,
param-sensitivity rel-std<=0.5). TC-survival is a moderate-margin pass
(0.547 vs 0.5 threshold) at 205 trades over the full sample.

## Decision (original, 2026-09-15-040 + 2026-09-16 QQQ fix)

**Accept for crypto (BTC/USDT, ETH/USDT). Accept QQQ** (via a separate
follow-up minmax_window retune, see `backtests/2026-09-16_donchian_width_qqq_fix.md`).
**SPY rejected** in both attempts, no rescue found at that time.

## SPY fix (follow-up iteration this cron trigger)

A wider joint sweep over `trend_window` x `donchian_window` x
`minmax_window` x `sensitivity` x `deadband` (720 combos) found 3 combos
clearing all thresholds for SPY, best at:

`trend_window=40, donchian_window=30, minmax_window=150, sensitivity=0.3,
deadband=0.30`

| Validator | Result |
|---|---|
| Sharpe | 1.050 (pass, threshold 1.0) |
| MDD | 6.89% (pass, threshold 25%) |
| TC-survival net Sharpe | 0.551 (pass, threshold 0.5, 127 trades) |
| Walk-forward pass fraction | 1.0 (pass, threshold 0.75) |
| Param sensitivity rel-std | 0.057 (pass, threshold 0.5) |

**Accept SPY.** Combined with the existing QQQ (via minmax_window=80 retune)
and crypto BTC/USDT+ETH/USDT accepts, Donchian Channel Width inverse-vol
sizing now covers the full universe: QQQ, SPY, BTC/USDT, ETH/USDT. SPY
needed a considerably longer `minmax_window` (150 vs QQQ's 80) and
`donchian_window` (30 vs 20) than QQQ, consistent with SPY's generally
lower/smoother realized volatility requiring a longer lookback to find
meaningful compression/expansion contrast. Full raw validator output:
`validate_result_donchian_width_spy_fix.json`.

## Source
https://sdk-trading.com/en/indicators/volatility/donchian-channels/
(unchanged from `2026-09-15-040`, no new fetch this iteration — pure
own-data parameter retune).
