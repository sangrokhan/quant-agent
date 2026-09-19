# DXY Absolute-Level Hysteresis Regime Gate — Backtest Report

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_dxy_absolute_level_hysteresis_regime.py`
**Outcome:** REJECTED

## Hypothesis

Per https://www.neverhodl.com/intelligence/learn/dxy-dollar-index-bitcoin
(and corroborating https://marginpad.io/blog/dxy-dollar-index-bitcoin/), the
US Dollar Index (DXY) has disclosed absolute "zones": DXY<90 = most
favorable weak-dollar risk-on regime (2017 and 2020-2021 BTC bull runs both
occurred with DXY<90); DXY 90-100 = neutral; DXY>105 = "significant
headwind" (2022 bear market coincided with DXY reaching 114). This iteration
tests a two-level HYSTERESIS state machine on those absolute levels: go/stay
long when DXY closes below `enter_level` (weak dollar), stay long
regardless of intermediate DXY moves until DXY closes above `exit_level`
(strong-dollar headwind), then go/stay flat until DXY drops below
`enter_level` again.

This construction (fixed absolute-level, two-threshold hysteresis, no
per-bar re-evaluation) is distinct from three prior DXY strategies already
in the knowledge base:
- 2026-09-05-026 (rejected): DXY vs its own 50d SMA, relative & re-evaluated
  every bar.
- 2026-09-09-113 (rejected): DXY rate-of-change momentum gate.
- 2026-09-11-058 (accepted SPY/QQQ, rejected EEM/crypto): UUP (dollar ETF
  proxy) vs its own SMA trend gate.

It reuses the exact hysteresis state-machine pattern already validated as a
genuinely distinct construction for VIX in this repo
(`2026-09-20_vix_absolute_level_hysteresis_regime.py`, id 2026-09-20-009,
accepted), applied here to DXY's own disclosed absolute zones instead.

## Grid test (Step 6)

`param_grid={"enter_level": [90, 95, 100], "exit_level": [103, 105, 108]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2017-01-01 to 2026-09-01.

- **total_cells:** 108, **passed_cells:** 18, **pass_fraction:** 0.167
- **by_asset_class:** equity 18/54 pass; crypto 0/54 pass (decisive crypto rejection)
- **by_vol_regime:** low 18/36 pass; mid 0/36; high 0/36 (edge concentrated
  entirely in the LOW-vol tercile; the strategy is essentially never
  invested outside quiet-dollar, quiet-equity conditions)
- **best_cell:** QQQ, low-vol, enter=100/exit=108, Sharpe 2.93 (single tercile slice)
- **worst_cell:** ETH/USDT, high-vol, enter=90/exit=105, Sharpe -0.29

All 18 passing cells are QQQ-low-vol or SPY-low-vol only — no mid/high-vol
cell and no crypto cell ever passed at any parameter combination.

## Single-config validation (Step 7) — enter_level=100, exit_level=105 (best full-sample-ish config)

| Symbol | Trades | Sharpe | MDD | Net Sharpe (10bps/trade) |
|---|---|---|---|---|
| QQQ | 5 | 0.907 (fail, thr 1.0) | 0.362 (fail, thr 0.25) | 0.903 (pass, thr 0.5) |
| SPY | 5 | 0.773 (fail, thr 1.0) | 0.341 (fail, thr 0.25) | 0.769 (pass, thr 0.5) |

Parameter sensitivity (QQQ, full-sample, 9-cell param grid across
enter/exit combos): relative_std=0.313 (pass, threshold 0.5) — the strategy
is at least *consistent* across nearby parameter choices, it just isn't
good enough on Sharpe/MDD at full-sample granularity.

Walk-forward validator (`check_walk_forward`) could not run this iteration
— `vectorbt.utils.splitting.RangeSplitter` raised `AttributeError: module
'vectorbt.utils' has no attribute 'splitting'` in the installed vectorbt
version (pre-existing repo/library issue, not specific to this strategy);
noted here for a future loop to fix the validator helper.

## Decision

**REJECTED.** Full-sample Sharpe and max-drawdown both fail on both QQQ and
SPY despite passing transaction-cost survival and parameter sensitivity.
The grid confirms the failure isn't a fluke of one config — the edge only
shows up when the low-vol-tercile grid slice is isolated (5 trades over
~9.5 years means the full-period metric is dominated by whichever few
multi-year holding periods happen to fall in higher-vol stretches, which
drag both Sharpe and MDD past their thresholds). Crypto is decisively
rejected in every cell (0/54), consistent with prior DXY-family findings
that the macro dollar-liquidity narrative doesn't transmit cleanly to a
mechanical single-asset backtest at this granularity. Distinct from, but no
more successful than, the two prior rejected DXY constructions (SMA-relative,
ROC) — absolute-level hysteresis does not rescue the DXY family.
