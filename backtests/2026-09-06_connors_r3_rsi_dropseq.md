# Backtest Report: Connors R3 -- 3-day RSI(2) Drop-Sequence Mean Reversion (2026-09-06)

**Hypothesis:** Per QuantifiedStrategies.com's writeup of Larry Connors' R3
strategy (Ch.4, "High Probability ETF Trading", 2009): close above the
200-day SMA; 2-day RSI drops 3 consecutive days with the first drop starting
from a reading below 60; enter long when 2-day RSI is below 10 today; exit
when 2-day RSI rises above 70.

**Source:** https://www.quantifiedstrategies.com/larry-connors-r3-strategy/

**Strategy file:** `strategies/2026-09-06_connors_r3_rsi_dropseq.py`

## Step 6 grid summary (`run_strategy_grid`)

- Grid: `entry_below` in {10, 15} x `exit_above` in {65, 70, 75} x symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} x vol regimes {low, mid, high}
- **72 total cells, 16 passed -- pass_fraction = 0.222**
- by_asset_class: equity 16/36 (44%), crypto 0/36 (0%)
- by_vol_regime: low 9/24 (37.5%), mid 5/24 (20.8%), high 2/24 (8.3%)
- best_cell: QQQ, entry_below=15, exit_above=65, low-vol regime, Sharpe=2.34
- worst_cell: SPY, entry_below=10, exit_above=75, high-vol regime, Sharpe=-0.20

Same qualitative pattern as the 2026-09-06 Double ROC acceleration strategy
tested earlier this run: works only on equities, concentrated in low/mid-vol
regimes, crypto sees 0 passing cells (0/36) across the whole grid.

## Step 7 single-config validators (best grid combo full-sample: QQQ, entry_below=15, exit_above=65)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.892 | >= 1.0 | FAIL (near-miss, 11% short of threshold) |
| Max drawdown | 0.099 | <= 0.25 | PASS |
| Transaction cost survival (net Sharpe, 10bps/trade, 43 trades) | 0.780 | >= 0.5 | PASS |
| Parameter sensitivity (relative std across 6 combos) | 0.216 | <= 0.5 | PASS |
| Walk-forward | not run | -- | `check_walk_forward` broken in installed vectorbt (`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`) -- pre-existing repo-wide tooling issue, not this strategy's fault. |

Sensitivity sweep shows Sharpe *improving* monotonically as `exit_above`
rises (0.62 -> 0.64 -> 0.78 for entry_below=10; 0.89 -> 0.97 -> 1.13 for
entry_below=15) -- `entry_below=15, exit_above=75` actually clears the 1.0
Sharpe bar (1.133) on QQQ full-sample. That specific combo wasn't the grid's
selected "best_cell" (grid picks per-regime-slice max, not full-sample max)
but is worth flagging for a future loop.

## Decision: REJECT (as tested config), flag as promising near-miss

Sharpe fails at the grid's nominal best-cell full-sample config (0.892 vs.
1.0 threshold) though every other validator passes cleanly and the miss
margin is small. A wider exit_above sweep (this run only tested up to 75)
combined with the low-vol-regime gate (as in the accepted
`2026-09-03_bb_meanrev_qqq_volregime.py`) looks like the most promising next
step -- unlike the Double ROC near-miss earlier this run, this one already
clears 1.0 Sharpe at `exit_above=75` on QQQ full-sample without any regime
gating at all. Crypto remains categorically unsuitable (0/36 grid cells).
