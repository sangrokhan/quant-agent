# Z-Score RSI Mean Reversion — Backtest Report (2026-09-20)

**Strategy file:** `strategies/2026-09-20_zscore_rsi_meanrev.py`
**Hypothesis source:** [StatOasis — "The Better-RSI Showdown: We Tested 4
RSI Upgrades on SPY, QQQ, IWM, and DIA"](https://statoasis.com/overfit/research/better-rsi-backtest)
(Ali Casey, published Sep 10 2026; 1,856-backtest study), visited via
`browser_exec` this iteration.

## Hypothesis

StatOasis's "Z-Score RSI" (Wilder RSI(14) re-expressed as a rolling
20-period z-score of the RSI reading itself, population std) beat the
plain-RSI baseline on median CAR (1.05% vs -0.15%), median CAR/MaxDD (0.030
vs 0.000), and median max drawdown (38.27% vs 40.65%) across
SPY/QQQ/IWM/DIA. The source's single best reliable (>=50 trades) variant
across all four RSI families tested was Z-Score RSI on QQQ Long:
rsi_len=14, z_lookback=20, entry z<=-2.0, exit z>=1.0, 5-bar time exit
(CAR/MaxDD 1.170, WinPct 64.8%, 182 trades).

## Grid test (Step 6)

`param_grid={"entry_z": [-2.0, -1.5], "exit_z": [0.5, 1.0], "max_hold_days":
[5, 10]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 96 total cells.

- **pass_fraction: 0.229** (22/96)
- by_asset_class: equity 22/48 passed; **crypto 0/48 passed (decisive fail)**
- by_vol_regime: low 16/32; mid 4/32; high 2/32 — edge concentrated in
  low-vol regimes
- best_cell: entry_z=-1.5, exit_z=1.0, max_hold_days=10, SPY, low-vol,
  Sharpe 2.13
- worst_cell: entry_z=-2.0, exit_z=1.0, max_hold_days=5, BTC/USDT, low-vol,
  Sharpe -1.07

## Single-config validation (Step 7) — best config (entry_z=-1.5,
exit_z=1.0, max_hold_days=10), full-period 2016-01-01 to 2026-09-01

| Metric | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe (full period) | 0.758 | 0.782 | >= 1.0 | **FAIL** (both) |
| Max drawdown | 21.46% | 18.96% | <= 25% | PASS |
| Net Sharpe after 5bps/trade costs | 0.666 | 0.659 | >= 0.5 | PASS |
| Walk-forward pass fraction (4 splits) | 1.00 | 1.00 | >= 0.75 | PASS |
| Parameter sensitivity (relative std, 8-combo sweep) | 0.168 | 0.188 | <= 0.5 | PASS |

## Decision: REJECTED

Sharpe ratio fails the >=1.0 threshold on both QQQ (0.758) and SPY (0.782)
at full-period, despite otherwise strong robustness (MDD, transaction-cost
survival, walk-forward 4/4, and low parameter sensitivity all pass). This
mirrors the source article's own framing: the median-across-family
improvement over plain RSI is real but "modest, not dramatic" — the
grid-best low-vol cells (Sharpe up to 2.13) do not generalize to the
full-period single-config Sharpe. Crypto is a decisive fail across the
entire grid (0/48 cells), consistent with this being a mean-reversion
construction tuned on US equity index behavior, not a broadly-applicable
edge.

This is a genuine near-miss (Sharpe ~0.76-0.78 vs 1.0 threshold, everything
else passing) — worth revisiting with either (a) a tighter low-vol-only
regime gate given the by_vol_regime split showing the edge concentrates in
low-vol (16/32 vs 4/32 mid, 2/32 high), following this repo's established
vol-regime-gate rescue pattern, or (b) restricting entries to the grid's
identified best cell parameters directly rather than averaging over the
full param grid.
