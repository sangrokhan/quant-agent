# Backtest Report: Formation-Price Stop-Loss Trend Overlay (2026-09-08)

**Status: ACCEPTED (QQQ only)** — SPY is a very close near-miss.

## Hypothesis

Per CXO Advisory's summary of Han, Zhou & Zhu "Taming Momentum Crashes: A
Simple Stop-Loss Strategy" (https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/),
imposing a fixed-percentage stop-loss from a position's FORMATION/entry
price on a conventional momentum strategy roughly doubled gross monthly
Sharpe (0.17 → 0.40 at a 15% threshold) and cut the worst monthly losses
from -49.8%/-39.4%/-35.2%/-34.5% to -17.4%/-14.8%/-13.8%/-13.1%.

Adapted single-asset time-series: long when `close > SMA(trend_window)`;
exit (go flat) if close falls below the entry price by more than
`stop_loss_pct`, or on a plain trend-flip; re-enter only on a fresh trend
signal.

## Single-config validator results (best grid config: `stop_loss_pct=0.10`, `trend_window=50`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.962 ❌ (narrow miss) | 0.215 ✅ | 0.855 ✅ | 1.0 ✅ | 0.059 ✅ | 66 |
| **QQQ** | **1.049 ✅** | **0.189 ✅** | **0.975 ✅** | **1.0 ✅** | **0.037 ✅** | **63** |

**QQQ passes all 5 validators — ACCEPTED.**

## Grid test summary

`param_grid={stop_loss_pct:[0.10,0.15,0.20], trend_window:[50,200]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 72 total cells.

- Overall pass_fraction: 0.25 (18/72 cells)
- By asset class: equity 18/36 passed, crypto 0/36
- By vol regime: low 12/24, mid 6/24, high 0/24
- Best cell: SPY, low-vol, Sharpe 2.661
- Worst cell: QQQ, high-vol, Sharpe -0.371

## Decision

**Accept for QQQ only** (config: `trend_window=50`, `stop_loss_pct=0.10`).
This is the second accepted strategy from this cron trigger's outer loop.
SPY is a very close near-miss (Sharpe 0.962, just under the 1.0 threshold —
every other validator passes comfortably, including MDD 0.215 and
walk-forward 1.0), worth a targeted SPY-specific local parameter refinement
in a future iteration (same pattern as prior successful refinements
2026-09-08-149/150/154/175). Crypto rejected decisively across all 36
cells — scope explicitly limited to QQQ equity only.
