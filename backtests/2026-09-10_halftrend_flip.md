# Backtest Report: HalfTrend Flip (everget construction)

**Strategy file:** `strategies/2026-09-10_halftrend_flip.py`
**Hypothesis / source:** everget's HalfTrend indicator
(https://www.tradingview.com/script/U1SJ8ubc-HalfTrend), source code
verified via GitHub (pradip-interra/PineScripts
`strategy_ht_ce_pd_rsi_combined.ps`, a v5 port of everget's original v4
script). Trading rule per source: go long on a trend flip from down(1) to
up(0); flatten on the mirror flip. See knowledge_base entry
`2026-09-10-013` for full hypothesis text and novelty rationale (distinct
two-stage state machine vs. SuperTrend/Chandelier Exit/Parabolic SAR/Gann
HiLo, all already tested in this repo as single-condition trailing flips).

## Grid test summary (Step 6)

- Grid: `amplitude` in {2,4,6} x `max_hold_days` in {30,60,90}, equity
  (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3.
- **pass_fraction: 0.231 (25/108)**
- by_asset_class: equity 25/54, crypto 0/54
- by_vol_regime: low 18/36, mid 7/36, high 0/36
- best_cell: amplitude=2, max_hold_days=30, QQQ, low-vol, Sharpe=3.08

A finer local sweep around the low-vol best cell (amplitude in {2,3,4},
max_hold_days in {20,25,30,40,50}) confirmed amplitude=2 as consistently
best across the full sample for QQQ; SPY peaked at a wider max_hold_days.

## Single-config validation (Step 7)

### QQQ, amplitude=2, max_hold_days=25 -- ACCEPTED

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.242 | >= 1.0 |
| Max drawdown | PASS | 0.230 | <= 0.25 |
| TC survival (5bps/trade, 52 trades) | PASS | net Sharpe 1.207 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 4/4 splits positive Sharpe (pass_fraction 1.0) | >= 0.75 |
| Parameter sensitivity (15-cell local grid) | PASS | relative_std 0.262 | <= 0.5 |

All validators pass for QQQ. **Accepted.**

### SPY, amplitude=2, max_hold_days=50 -- REJECTED (near-miss)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL (near-miss) | 0.996 | >= 1.0 |
| Max drawdown | PASS | 0.177 | <= 0.25 |
| TC survival | PASS | net Sharpe 0.950 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 3/4 positive (0.75) | >= 0.75 |

SPY misses the Sharpe threshold by a hair (0.004) across every
max_hold_days tested in the local sweep (best observed 0.996-0.998).
Rejected as a documented near-miss -- a future iteration could revisit
with a slightly different exit rule (e.g. an explicit ATR trailing stop
using the source's own `atrHigh`/`atrLow` channel bands, currently unused
here) to try to close this narrow gap.

### Crypto (BTC/USDT, ETH/USDT) -- REJECTED (decisive)

0/54 grid cells passed across all vol regimes and parameter combinations.
The HalfTrend flip signal does not translate to crypto's return
distribution at daily-bar granularity.

## Scope note

Accepted for **QQQ only** (amplitude=2, max_hold_days=25). Not accepted
for SPY (near-miss) or crypto (decisive fail). A future loop should not
assume this strategy generalizes beyond QQQ without further work on the
SPY near-miss or a fresh crypto-specific parameterization.
