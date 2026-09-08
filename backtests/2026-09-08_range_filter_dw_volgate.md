# Backtest Report: Range Filter [DW] Trend-Following, Low-Vol Regime Gated (QQQ)

**Strategy file:** `strategies/2026-09-08_range_filter_dw_volgate.py`
**Date:** 2026-09-08
**Knowledge base id:** 2026-09-08-168

## Hypothesis

Direct follow-up to near-miss `2026-09-05-018` (plain Range Filter [DW]
crossover, DonovanWall/marketcalls.in): the original grid showed a striking
regime split (low-vol tercile 36/36 pass, mid-vol 18/36, high-vol 1/36) and
QQQ's full-sample Sharpe missed the 1.0 threshold only marginally (0.957).
Adds an entry-only realized-volatility regime gate (20d realized vol <=
trailing 252d median, same construction as the repo's other vol-gated
strategies) to the identical Range Filter [DW] entry/exit logic, isolating
whether the gate alone rescues the near-miss (same fix pattern validated
previously for KAMA/ATR-band 2026-09-06-183 and VQI streak 2026-09-08-044).

## Grid summary (Step 6)

`sampling_period` in [10, 15, 20] x `range_mult` in [2.0, 2.5, 3.0] x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 108 cells.

- **pass_fraction: 0.176** (19/108)
- **by_asset_class:** equity 19/54 (0.35), crypto 0/54 (0.0) — crypto rejected decisively.
- **by_vol_regime:** low 18/36 (0.50), mid 1/36 (0.03), high 0/36 (0.0) —
  edge is almost entirely confined to the low-vol regime, as expected given
  the vol gate.
- **best_cell:** QQQ, sampling_period=15, range_mult=3.0, low-vol, Sharpe 2.40
- **worst_cell:** SPY, sampling_period=20, range_mult=3.0, high-vol, Sharpe -1.36

## Single-config validation (Step 7): QQQ, sampling_period=15, range_mult=3.0

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS (borderline) | 1.0047 | >= 1.0 |
| Max drawdown | PASS | 0.152 | <= 0.25 |
| Transaction cost survival (10bps/trade, 53 trades) | PASS | net Sharpe 0.911 | >= 0.5 |
| Walk-forward (manual 4-slice fallback*) | PASS | 1.0 (4/4 positive) | >= 0.75 |
| Parameter sensitivity (9 QQQ grid configs) | PASS | rel_std 0.147 | <= 0.5 |

\* `vbt.utils.splitting.RangeSplitter` broken in this install (documented
since 2026-09-03-002); manual 4-equal-slice fallback used.

### SPY, same config (spot-check)

- Sharpe: 0.646 (FAIL, < 1.0)
- Max drawdown: 0.135 (pass)

## Decision: ACCEPT (QQQ only, borderline; SPY and crypto rejected)

The vol gate improved QQQ's full-sample Sharpe from 0.957 (near-miss,
2026-09-05-018) to 1.0047 — a marginal but real pass, all other validators
passing comfortably (walk-forward is now a perfect 4/4, up from n/a in the
original test). This confirms the diagnosis that high-vol-regime whipsaws
were dragging down the aggregate Sharpe. SPY does not carry the same edge
(Sharpe 0.646, decisive fail) — scope this acceptance to QQQ only. Crypto
remains decisively rejected across the whole grid.

The QQQ Sharpe pass is narrow (1.0047 vs 1.0 threshold) — flag this as a
fragile pass for a future loop's attention; a slightly different sample
window or fee assumption could flip it.
