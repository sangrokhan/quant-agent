# Backtest Report: Gold/Bitcoin Dual Momentum — Composite (3-Lookback Average)

**Strategy file:** `strategies/2026-09-23_gold_bitcoin_dual_momentum_composite.py`
**Date:** 2026-09-23

## Hypothesis

Source: Quantpedia "Dual Momentum Allocation Between Physical Gold and
Bitcoin (Digital Gold)" (R. Vojtko, C. Dujava, 6 May 2026),
https://quantpedia.com/dual-momentum-allocation-between-physical-gold-and-bitcoin-digital-gold/
(already visited/tested in this repo as 2026-09-13-003, single-lookback,
accepted).

New source for this iteration: Aligrithm's "6.58 Dual Momentum Between
Gold and Bitcoin (Two Stores of Value)" (14 Aug 2026),
https://aligrithm.com/dual-momentum-between-gold-and-bitcoin-two-stores-of-value/
— makes explicit that the source's headline low-risk result (12.01%/yr,
Sharpe 1.37, MDD -12.27%) is a **composite averaging 3 independent
single-lookback (4/8/12-week) dual-momentum sub-strategies**, each
individually vol-capped at 20%, NOT a single-lookback result. Source's own
stated rationale: averaging diversifies away idiosyncratic single-lookback
whipsaw (an 8-week window "stays positive deep into a decline, then flips
after the damage is already on the sheet").

This repo's existing 2026-09-13-003 implements only the single 8-week
lookback (MDD 23.1%). This iteration tests the genuinely distinct
composite-averaging mechanic.

## Primary config

`vol_cap=0.20, lookback_weeks_1=4, lookback_weeks_2=8, lookback_weeks_3=12`, GLD primary / BTC-USDT partner (internal), 2019-01-01 to 2026-09-01.

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.755 | ≥1.0 | ✅ |
| Max drawdown | 0.186 | ≤0.25 | ✅ |
| TC survival (10bps/trade, 19 trades) | net Sharpe 1.735 | ≥0.5 | ✅ |
| Walk-forward (4 splits) | 0.75 (3/4 positive) | ≥0.75 | ✅ |
| Parameter sensitivity (vol_cap sweep 0.15/0.20/0.25) | rel. std 0.0054 | ≤0.5 | ✅ |

**All 5 validators pass.**

Comparison to sibling single-lookback strategy (2026-09-13-003, 8-week
only): Sharpe 1.503 → 1.755 (composite better), MDD 0.231 → 0.186
(composite materially better, confirming source's own claim that
averaging reduces drawdown), TC-survival and param-sensitivity both
comparable/strong in both.

## Grid summary (Step 6)

`run_strategy_grid`, GLD + SLV (equity asset class only — BTC/USDT is
fetched internally as the partner leg, not gridded as a primary symbol),
vol_regime_splits=3, vol_cap in {0.15, 0.20, 0.25}, lookbacks fixed at
4/8/12 weeks:

- **18 total cells, 14 passed (pass_fraction = 0.778)**
- By asset class: equity 14/18
- By vol regime: low 3/6, mid 6/6, high 5/6
- Best cell: GLD, vol_cap=0.15, low-vol regime, Sharpe 2.326
- Worst cell: GLD, vol_cap=0.15, high-vol regime, Sharpe 1.018 (still positive/passing)

Holds broadly across both GLD and SLV as the "gold-like" primary leg, and
across vol regimes (weakest but still majority-passing in the low-vol
tercile, likely because BTC dual-momentum switches are rarer/smaller in
absolute-return terms when overall market vol is already low).

## Decision

**ACCEPTED.** All validators pass at the primary config; grid pass
fraction 77.8% across GLD/SLV and vol regimes. Kept live in `strategies/`.
