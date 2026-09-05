# Backtest Report: Coppock Curve Trough-Turn Entry

**Strategy file:** `strategies/2026-09-06_coppock_trough_turn.py`
**Date:** 2026-09-06
**Outcome:** ACCEPTED (SPY only); REJECTED (QQQ, crypto)

## Hypothesis

Per a Google AI-overview synthesis of Coppock Curve strategy guides
(LightningChart/TradingView explainers): besides the standard zero-line
crossover entry, "some traders buy when the indicator line simply turns
upward from a trough while still below zero" -- an earlier, more
aggressive trigger. This tests that trough-turn rule (curve turns from
falling to rising while still <0) vs. this repo's already-tested standard
zero-cross version (2026-09-04-036, accepted QQQ only, SPY near-miss,
crypto rejected), keeping the same daily-frequency-with-monthly-ROC-periods
(11,14) setup for direct comparability.

Source: Google AI overview synthesis, query "Coppock Curve momentum
indicator trading strategy rules parameters" (2026-09-06).

## Grid test summary (Step 6)

`param_grid={"wma_window": [8,10,14], "max_hold_days": [10,20,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.167** (18/108)
- By asset class: equity 18/54, **crypto 0/54** (decisive reject)
- By vol regime: low 3/36, mid 9/36, high 6/36 (edge concentrated in
  mid/high-vol, unlike many prior strategies here that favor low-vol)
- Best cell: SPY, wma_window=14, max_hold_days=20, high-vol regime,
  Sharpe=1.72
- Worst cell: SPY, wma_window=10, max_hold_days=10, low-vol regime,
  Sharpe=-0.76
- Best shared config: wma_window=14, max_hold_days=20 (QQQ 2/3 vol regimes
  pass, SPY 1/3 pass)

## Single-config validation (Step 7) — wma_window=14, max_hold_days=20

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.486 — **FAIL** | 1.079 — PASS | >= 1.0 |
| Max drawdown | 0.191 — PASS | 0.116 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.316 — **FAIL** | 0.824 — PASS | >= 0.5 net Sharpe |
| Parameter sensitivity | 0.486 (relative_std, borderline) — PASS | 0.305 — PASS | <= 0.5 |
| Walk-forward | not run — pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version | — | — |

Trades: QQQ=108, SPY=94 over 2019-01 to 2026-09 (1927 daily bars). QQQ's
much higher trade count vs. SPY at the same config drags its net-of-cost
Sharpe down heavily (0.108 total cost drag vs 0.094).

## Decision

**Accept for SPY only.** SPY passes Sharpe, max drawdown, transaction cost
survival, and parameter sensitivity at wma_window=14/max_hold_days=20.
**Reject for QQQ**: full-sample Sharpe (0.486) and net-of-cost Sharpe
(0.316) both miss threshold — QQQ's higher trade frequency at this config
overtrades relative to its edge. **Reject for crypto**: 0/54 grid cells
passed.

## Notes for future loops

Interesting reversal vs. the standard zero-cross Coppock variant
(2026-09-04-036, which favored QQQ and near-missed SPY) — here the
trough-turn (earlier) entry favors SPY instead. The two entry styles seem
to have asset-specific edges rather than one being strictly better. Also
notable: this strategy's edge concentrates in mid/high-vol regimes (unlike
most mean-reversion-style strategies in this KB which favor low-vol) —
consistent with Coppock being a momentum/trend-turning indicator that
benefits from larger moves. A future loop could try adding an explicit
regime filter requiring mid/high vol as an entry gate to sharpen this.
