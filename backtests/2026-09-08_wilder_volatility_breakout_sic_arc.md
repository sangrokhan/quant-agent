# 2026-09-08 Wilder Volatility Breakout (SIC/ARC) Trend-Following (QQQ, SPY) — ACCEPTED

**Hypothesis:** J. Welles Wilder's original Volatility System (New Concepts
in Technical Trading Systems, 1978), per the exact ARC/SIC/SAR formula at
https://oxfordstrat.com/trading-strategies/volatility-breakout/: ARC =
ATR(atr_length) x arc_constant is a volatility-scaled breakout distance;
SIC tracks the extreme favorable close reached. Long-only adaptation for
SAFETY.md: enter when close breaks above (rolling low anchor + ARC); while
long, trail the running-max close (SIC_high) minus ARC as a stop, backed by
a fixed ATR-multiple stop-loss set at entry (atr_stop_mult=6, per source's
own auxiliary spec) and a max_hold_days time-stop.

Source: https://oxfordstrat.com/trading-strategies/volatility-breakout/
(exact ARC/SIC/SAR formula + original 42-futures-market backtest spec).
First Wilder Volatility System / SIC-ARC-SAR strategy in this repo --
distinct from prior ATR-trailing-stop strategies (Chandelier Exit, Chande
Kroll Stop, SuperTrend) which trail from highest-high/EMA rather than a
running favorable-close (SIC) anchor.

## Grid test (Step 6)

`param_grid = {arc_constant: [2.0, 3.0, 4.0], max_hold_days: [20, 40]}`,
`symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall pass fraction: 19/72 (26.4%)**
- By asset class: equity 19/36, crypto 0/36 (decisive crypto rejection)
- By vol regime: low 12/24, mid 6/24, high 1/24
- Best cell: QQQ, low-vol, `arc_constant=3.0, max_hold_days=40`, Sharpe 2.75
- Worst cell: QQQ, high-vol, `arc_constant=4.0, max_hold_days=20`, Sharpe -0.40

## Single-config validators (Step 7): QQQ, arc_constant=3.0, max_hold_days=40, full sample 2019-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ PASS | 1.275 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 20.0% | ≤ 25% |
| Transaction cost survival (10bps/trade, 45 trades) | ✅ PASS | net Sharpe 1.215 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` unavailable in this install) | ✅ PASS | 4/4 splits positive (100%) | ≥ 75% |
| Parameter sensitivity (6-point sweep: arc_constant×max_hold_days) | ✅ PASS | relative_std 0.140 | ≤ 0.5 |

SPY sanity check, same config: Sharpe 1.255, MDD 13.0% — consistent with
QQQ, confirms this isn't a single-ticker artifact.

## Decision: ACCEPTED (equity only — QQQ and SPY)

All 5 validators pass on the primary config. Scope is honestly narrow:
strongest in low-vol regimes (12/24 grid passes vs only 1/24 in high-vol),
and crypto is rejected decisively (0/36 grid cells) — likely because
`lookback=20`-bar close-based entry + a 40-bar max-hold time-stop is tuned
for daily-equity-scale trends and doesn't translate to crypto's 1h-bar
volatility regime as configured. Kept live in `strategies/`; future loops
should not assume this holds outside equity/low-to-mid-vol daily bars.
