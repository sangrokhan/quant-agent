# SPY/TLT/EEM Monthly Momentum Rotation — Backtest Report (2026-09-20)

**Strategy file:** `strategies/2026-09-20_spy_tlt_eem_momentum_rotation.py`
**Hypothesis source:** [QuantifiedStrategies — "ETF Rotation Strategy for
High Returns"](https://www.quantifiedstrategies.com/etf-rotation-strategy/),
visited via `browser_exec` this iteration.

## Hypothesis

Source ranks SPY, TLT, EEM monthly by trailing return, holds only the
single best performer for the next month. Source's own 3-month-lookback
variant: CAGR 11.5%, MaxDD 32% (2003-2026, no costs). Adapted to this
repo's single-primary-asset interface: go long the primary asset only in
months where its own trailing momentum beats both TLT and EEM; flat
otherwise (a "rotate into me or stay flat" gate rather than literal 3-way
capital rotation, since the interface returns one position series per call).

## Grid test (Step 6)

`param_grid={"lookback_days": [21, 63, 126]}` (1/3/6-month approximations),
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 36 total cells.

- **pass_fraction: 0.25** (9/36)
- by_asset_class: equity 8/18 passed; crypto 1/18 passed
- by_vol_regime: low 7/12; mid 2/12; high 0/12 — edge concentrated in
  low-vol regimes, zero passes in high-vol
- best_cell: lookback_days=63 (matches source's own best 3-month lookback
  finding), QQQ, low-vol, Sharpe 2.39
- worst_cell: lookback_days=126, QQQ, high-vol, Sharpe -0.80

## Single-config validation (Step 7) — lookback_days=63 (grid-best, matches
source's own preferred setting), full-period 2016-01-01 to 2026-09-01

| Metric | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe (full period) | 0.808 | 0.207 | >= 1.0 | **FAIL** (both) |
| Max drawdown | 21.78% | 33.40% | <= 25% | QQQ PASS / SPY **FAIL** |
| Net Sharpe after 5bps/trade costs | 0.795 | 0.182 | >= 0.5 | QQQ PASS / SPY **FAIL** |
| Walk-forward pass fraction (4 splits) | 1.00 | 0.50 | >= 0.75 | QQQ PASS / SPY **FAIL** |
| Parameter sensitivity (relative std, 3-value sweep) | 0.483 | 0.658 | <= 0.5 | QQQ PASS / SPY **FAIL** |

## Decision: REJECTED

SPY fails every single validator decisively. QQQ is a near-miss on Sharpe
alone (0.808 vs 1.0) but passes all other validators including a clean
walk-forward (4/4). This asymmetry between QQQ and SPY is itself notable:
QQQ's higher baseline momentum/volatility apparently interacts better with
a 3-month relative-strength rotation gate than SPY's, which is the
opposite of what the source article (which only tested SPY as the primary
risk leg, never QQQ) would predict. The grid's near-zero high-vol-regime
pass rate (0/12) also confirms this construction is not robust across
volatility regimes even where it does pass. Crypto is essentially a
decisive fail (1/18).

Worth flagging for a future iteration: QQQ specifically is a genuine
near-miss (everything but Sharpe passes cleanly) — could be revisited with
either a tighter parameter search around lookback_days near 63, or gating
entries to the low-vol regime explicitly (matches the by_vol_regime
breakdown pattern seen repeatedly in this repo's accepted vol-gated
strategies).
