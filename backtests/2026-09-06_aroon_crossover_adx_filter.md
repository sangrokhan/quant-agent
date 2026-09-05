# Backtest Report: Aroon Crossover + ADX Trend-Strength Filter

**Strategy file:** `strategies/2026-09-06_aroon_crossover_adx_filter.py`
**Date:** 2026-09-06
**Outcome:** REJECTED

## Hypothesis

Per Capital.com's Aroon indicator guide ("A crossover of Aroon up above
Aroon down carries more weight when the crossing line is already above 50
at the point of crossing" and "Pairing Aroon with ADX helps confirm whether
a crossover is occurring in a genuinely trending environment worth
analysing further"), a long entry fires when AroonUp crosses above
AroonDown, AroonUp>50 at the cross, and ADX(14)>adx_threshold. Exit on
reverse cross, ADX dropping below threshold, or a 15-day time-stop.

Source: https://capital.com/en-int/learn/technical-analysis/aroon-indicator

Distinct from prior KB Aroon entries (2026-09-04-031 single-line
absolute-threshold state; 2026-09-04-063 oscillator zero-cross;
2026-09-05-079 dual-line simultaneous 70/30 threshold state) — this is the
first Aroon strategy in this repo gated by an explicit crossover EVENT
combined with an ADX trend-strength filter.

## Grid test summary (Step 6)

`param_grid={"aroon_window": [20,25,30], "adx_threshold": [20,25,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 total cells, threshold Sharpe used by grid_test's
internal pass criteria).

- Overall pass_fraction: **0.148** (16/108)
- By asset class: equity 16/54 passed, **crypto 0/54 passed** (decisive
  reject on crypto)
- By vol regime: low 9/36, mid 5/36, high 2/36 (edge concentrated in
  low-vol regimes, degrades sharply in high-vol)
- Best cell: QQQ, aroon_window=20, adx_threshold=20.0, low-vol regime,
  Sharpe=2.18
- Worst cell: QQQ, aroon_window=20, adx_threshold=30.0, high-vol regime,
  Sharpe=-0.22
- Best shared equity config (QQQ+SPY both pass 2/3 vol regimes):
  aroon_window=25, adx_threshold=20.0

## Single-config validation (Step 7) — aroon_window=25, adx_threshold=20.0

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.728 — **FAIL** | 0.608 — **FAIL** | >= 1.0 |
| Max drawdown | 0.127 — PASS | 0.055 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.668 — PASS | 0.509 — PASS | >= 0.5 net Sharpe |
| Parameter sensitivity | NaN (relative_std blew up: one grid cell near-zero mean sharpe) — **FAIL** | same — **FAIL** | <= 0.5 |
| Walk-forward | not run — pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version (same known issue noted in several recent entries) | — | — |

Trades: QQQ=22, SPY=20 over 2019-01 to 2026-09 (1927 daily bars).

## Decision

**Reject.** Full-sample Sharpe ratio (0.728 QQQ / 0.608 SPY) misses the 1.0
threshold on the best shared config despite decent per-regime Sharpes in
the grid (best single cell 2.18 in QQQ low-vol) — the grid's best cells are
concentrated in specific vol-regime/param combos that don't hold up when
averaged over the full sample. Crypto rejected decisively (0/54 grid
cells). Parameter sensitivity also failed due to high variance across the
grid (near-zero-mean cells inflate relative_std to NaN/very large).

## Notes for future loops

The best individual grid cells (QQQ low-vol, aroon_window~20,
adx_threshold=20, Sharpe 2.18) suggest low-vol-regime-only deployment might
be worth revisiting with an explicit vol-regime gate added to the entry
condition (similar pattern to `2026-09-03_bb_meanrev_qqq_volregime.py`)
rather than trading through all vol regimes unconditionally as this
version does. Also worth trying `aroon_up_strength` values other than the
default 50 (untested in this grid) since the source specifically flags
strength-at-crossing as a meaningful discriminator.
