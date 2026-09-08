# Backtest Report: Mayer Multiple Contrarian Accumulation (BTC/USDT-style valuation ratio, tested cross-asset)

**Hypothesis:** The Mayer Multiple (close / 200-day SMA) is a well-known
Bitcoin valuation heuristic. Per
https://www.theinvestorspodcast.com/bitcoin-mayer-multiple/, a multiple >=
2.4x marks historically overheated conditions, while the long-run average
(~1.47x) marks a reasonable accumulation zone. Tested here as a systematic
long-only rule: enter long when Mayer Multiple <= entry_threshold, exit to
flat when it spikes to >= exit_threshold, or a max_hold_days time-stop.
Applied to both crypto (its native domain) and equities (QQQ/SPY, as a
generalization of "price relative to 200d trend" valuation banding).

**Source:** https://www.theinvestorspodcast.com/bitcoin-mayer-multiple/
(visited this iteration via browser_exec after web_search backend errors).

## Step 6 grid summary

`entry_threshold` in [1.2, 1.47, 1.7] x `exit_threshold` in [2.0, 2.4],
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.
total_cells=72, passed_cells=18, **pass_fraction=0.25**.

- by_asset_class: equity 18/36 passed; **crypto 0/36 passed** (the
  strategy's own native asset class failed decisively -- crypto is far too
  volatile for the 25% MDD threshold even in cheap-valuation cells).
- by_vol_regime: low 12/24, mid 6/24, **high 0/24** -- passes concentrate
  entirely in low-vol regime slices, a classic cherry-picking pattern.
- best_cell: SPY, low-vol, Sharpe 2.44 (entry/exit thresholds don't matter
  in this cell -- signal barely varies across the parameter grid, another
  red flag re: threshold insensitivity/degenerate signal in that slice).
- worst_cell: BTC/USDT, high-vol, Sharpe 0.09.

## Step 7 single-config validation (entry=1.47, exit=2.4, max_hold=180)

| Symbol | Sharpe | MDD | Txn cost survival |
|---|---|---|---|
| SPY (2010-2026) | 0.908 (fail, need >=1.0) | 0.320 (**fail**, need <=0.25) | net Sharpe 0.897 (pass) |
| QQQ (2010-2026) | 1.060 (pass) | 0.347 (**fail**, need <=0.25) | not run (MDD already decisive) |

`check_walk_forward` errored on a pre-existing vectorbt API mismatch in
`validation/validators.py` (`vbt.utils.splitting` missing attribute) --
not rerun; not needed since MDD already fails decisively on both tested
equities full-sample. `check_parameter_sensitivity` not run given the same
reason.

## Step 8 decision: **REJECT**

Full-sample max drawdown fails the 25% ceiling on both QQQ (34.7%) and SPY
(32.0%) -- the strategy holds through multi-year drawdowns whenever the
Mayer Multiple stays below the exit threshold without spiking, so a
prolonged bear market with no valuation spike offers no exit trigger.
Grid pass_fraction of 0.25 is driven almost entirely by low-vol-regime
slices; crypto (the indicator's own native domain) failed 0/36 grid cells
outright, undermining the core Mayer Multiple thesis in this
implementation.
