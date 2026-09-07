# Inverse Head and Shoulders Neckline Breakout -- QQQ -- Backtest Report

**Strategy file:** `strategies/2026-09-08_inverse_head_shoulders_neckline.py`
**Hypothesis id:** 2026-09-08-109
**Source:** Google SERP snippets (IG.com, Vantage Markets, naga.com) -- inverse
head and shoulders: 3-trough reversal (left shoulder, deeper head, right
shoulder roughly symmetric to left), neckline through the two intermediate
swing highs; long entry on decisive close above neckline; stop below right
shoulder; measured-move target = (neckline - head) distance projected up
from breakout.

## Config tested (best grid cell)
- `pivot_window=11`, `target_multiple=1.5`
- Symbol: QQQ, 2019-01-01 to 2026-09-01, daily bars

## Single-config validator results

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.151 | >= 1.0 | PASS |
| Max drawdown | 11.32% | <= 25% | PASS |
| Transaction cost survival (10bps/trade, 21 trades) | net Sharpe 1.104 | >= 0.5 | PASS |
| Walk-forward (manual 4-split stand-in; vbt RangeSplitter broken in installed vectorbt 1.1.0, known repo scaffold bug) | 4/4 splits positive Sharpe [0.845, 0.470, 1.788, 0.697] (1.0 pass fraction) | >= 0.75 | PASS |

## Grid-test summary (Step 6)

`param_grid={pivot_window:[7,9,11], target_multiple:[1.0,1.5]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
72 total cells, 2019-2026.

- **pass_fraction: 0.208** (15/72)
- by_asset_class: equity 15/36 (42%), crypto 0/36 (0% -- fails entirely on crypto)
- by_vol_regime: low 12/24, mid 3/24, high 0/24 (concentrated in low-vol regime)
- best_cell: QQQ, pivot_window=11, target_multiple=1.5, low-vol, Sharpe 2.589
- worst_cell: SPY, pivot_window=11, target_multiple=1.0, high-vol, Sharpe -0.951

## Scope / honesty note

Edge is concentrated in **equity, low-vol regime** (12/24 low-vol cells pass
vs 3/24 mid-vol and 0/24 high-vol). Crypto shows zero passing cells (0/36).
Accept scope: **equity only (QQQ primary, SPY secondary), low-vol regime
preferred, pivot_window=11/target_multiple=1.5 config**. Do not deploy on
crypto or expect robustness through high-vol regimes.

## Decision: ACCEPT (scoped to equity, primarily low-vol regime)
