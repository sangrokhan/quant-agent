# Mass Index RSI Oscillator + SMA200 Trend Gate — Backtest Report

**Date:** 2026-09-07 | **Strategy file:** `strategies/2026-09-08_mass_index_rsi_oscillator_trendgate.py`

## Hypothesis

Per Donald Dorsey's Mass Index (via https://www.quantifiedstrategies.com/mass-index-trading-strategy/,
source discloses exact formula and its own backtested rule): the Mass
Index (`sum_25(EMA9(range)/EMA9(EMA9(range)))`) is non-directional, but the
source's own concrete directional variant takes a 5-day RSI of the Mass
Index and trades its extremes ("buy when RSI closes below 25, sell when
RSI closes above 75"). Source's own bare backtest (FXI, no trend filter)
was weak/erratic (189 trades, avg gain 0.83%/trade, max DD ~40%, profit
factor never >1.7 across many assets tried).

This repo's adaptation: add a standard SMA200 long-only uptrend gate to
the entry (only "buy the RSI-dip" while price > SMA200), on the
hypothesis that a trend filter would rescue the source's own
disclosed-weak edge, consistent with this repo's general pattern that
oscillator-only entries need a trend filter to survive costs.

## Step 6 — Grid summary (18 param combos x 4 symbols x 3 vol regimes = 216 cells)

- **Overall pass_fraction: 36/216 = 16.7%**
- By asset class: equity 36/108 (33.3%), crypto 0/108 (0%, decisive fail)
- By vol regime: low 36/72 (50%), mid 0/72 (0%, decisive fail), high 0/72 (0%, decisive fail)
- Best cell: QQQ, low-vol, entry=20/exit=70/hold=15, Sharpe 2.43
- Worst cell: SPY, mid-vol, entry=25/exit=80/hold=10, Sharpe -0.63
- **Pattern:** edge (where present at all) is confined entirely to the
  low-volatility tercile on equities only; every mid-vol, high-vol, and
  crypto cell fails decisively. This mirrors Dorsey/source's own
  disclosed "weak and erratic" bare-strategy finding — the SMA200 trend
  gate did NOT rescue it broadly, only concentrates whatever edge exists
  into calm markets.

## Step 7 — Single-config validation (entry=25/exit=75/hold=15, QQQ & SPY)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.377 ❌ | 0.287 ❌ | ≥ 1.0 |
| Max drawdown | 0.195 ✅ | 0.139 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | net Sharpe 0.286 ❌ | net Sharpe 0.154 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-quarter fallback) | 2/4 splits ❌ | 2/4 splits ❌ | ≥ 75% |
| Parameter sensitivity | rel_std 0.210 ✅ | rel_std 0.189 ✅ | ≤ 0.5 |

(Walk-forward uses the manual 4-equal-slice contiguous fallback, matching
this repo's precedent, since `vbt.utils.splitting` is unavailable in this
environment's vectorbt build.)

## Step 8 — Decision: **REJECTED**

Full-sample Sharpe, TC-survival, and walk-forward all fail on both QQQ
and SPY. The grid's low-vol-only pass pattern confirms the edge is real
but narrow (mirrors source's own weak/erratic disclosed finding), and the
full-sample validators — which blend all three vol regimes — correctly
fail because 2 of 3 regimes decisively lose money. Crypto is a decisive
0/108 reject across the board. MDD and parameter-sensitivity both pass,
so this is not a fundamentally broken construction — it's a genuine but
narrow low-vol-only equity edge, consistent with several other rejected
near-misses already in this knowledge base (KAMA/ATR-band, Kirshenbaum
Bands, etc.).
