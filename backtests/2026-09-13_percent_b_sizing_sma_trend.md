# Bollinger %B Continuous Sizing Overlay on SMA(200) Trend Gate

**Hypothesis:** Per Wikipedia/Fidelity/GoCharting (browser_exec Google SERP
synthesis): %B (John Bollinger) = (close - lower_band) / (upper_band -
lower_band). This repo has 4 prior %B strategies, all rejected, all using
%B as a binary ENTRY/EXIT threshold. This iteration instead uses %B as a
CONTINUOUS SIZING overlay: within an SMA(200) uptrend, exposure =
base_exposure - pb_sensitivity*(%B - 0.5), clipped to [0, leverage_cap] --
add exposure on pullbacks toward the lower band, reduce exposure when
stretched toward the upper band. Structurally distinct from every
risk-ratio sizing overlay tested elsewhere in this cron trigger (%B is a
forward-looking relative-positioning signal, not a backward-looking risk/
return ratio) and from the repo's existing %B entry-threshold strategies.
First %B-as-continuous-sizing strategy in this repo.

**Source:** https://en.wikipedia.org/wiki/Bollinger_Bands (via Google SERP
snippet, browser_exec)

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
base_exposure in [0.7,0.9,1.0], pb_sensitivity in [0.3,0.6,0.9];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, base_exposure=0.9, pb_sensitivity=0.3, low-vol, Sharpe=2.863
- worst_cell: ETH/USDT, base_exposure=1.0, pb_sensitivity=0.9, mid-vol, Sharpe=0.025

## Single-config validator results (best full-sample config per symbol:
base_exposure=1.0, pb_sensitivity=0.3, bb_window=20, bb_std=2.0,
trend_window=200)

| Symbol | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 0.979 | No (thr 1.0) | 0.199 | Yes | 0.945 | Yes | 0.75 | Yes | 0.031 | Yes |
| QQQ | 1.241 | Yes | 0.216 | Yes | 1.229 | Yes | 0.75 | Yes | 0.036 | Yes |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold); both symbols hit 3/4.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ. SPY fails only the
Sharpe threshold (0.979 < 1.0, a near-miss by 0.021) with every other
validator passing comfortably, including an unusually tight parameter
sensitivity (0.031) -- worth revisiting SPY with a wider bb_window sweep in
a future iteration. Crypto (BTC/USDT, ETH/USDT) rejected decisively across
the whole grid (0/54 cells).
