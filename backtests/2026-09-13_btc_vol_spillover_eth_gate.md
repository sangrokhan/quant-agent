# Backtest Report: BTC Volatility-Spike Gate on ETH Trend-Following (2026-09-13)

## Hypothesis
Per https://aligrithm.com/crypto-isnt-structurally-alien-roll-vpin-amihud-predict-distribution-shifts/
(critical re-analysis of Easley/O'Hara/Yang/Zhang's crypto microstructure
paper, read via browser_exec), after correcting for estimator artifacts in
most of the paper's headline findings, one survives a Bonferroni-corrected
robustness check: BTC/ETH's own Roll-measure (a volatility proxy) is the
only cross-coin feature with importance for predicting the SIGN of next-day
realized-volatility CHANGES in smaller altcoins -- i.e. BTC/ETH volatility
leads smaller-coin volatility ~1 day ahead. Adapted (loaders only cover
BTC/ETH) as: gate an ETH SMA-trend-following strategy to go flat for
`cooldown_days` after a BTC realized-vol spike (>= `btc_vol_spike_percentile`
of its trailing distribution), hypothesizing this avoids ETH's own
anticipated volatility expansion.

Source URL: https://aligrithm.com/crypto-isnt-structurally-alien-roll-vpin-amihud-predict-distribution-shifts/

## Strategy file
strategies/2026-09-13_btc_vol_spillover_eth_gate.py

## Step 6 grid summary (ETH/USDT only -- crypto-specific hypothesis, no equity analog; btc_vol_spike_percentile=[0.85,0.90,0.95] x cooldown_days=[2,3,5], vol_regime_splits=3, 2018-2026)

- total_cells: 27, passed_cells: 0, pass_fraction: 0.0 (decisive failure)
- by_vol_regime: low 0/9, mid 0/9, high 0/9 (fails uniformly across all regimes)
- best_cell: btc_vol_spike_percentile=0.95/cooldown_days=3, high-vol regime, Sharpe only 0.371
- worst_cell: btc_vol_spike_percentile=0.85/cooldown_days=3, low-vol regime, Sharpe -0.047

## Decision: REJECTED at grid stage (decisive, no near-miss)

0/27 grid cells pass across every parameter combination and every
volatility regime tercile; best cell Sharpe (0.371) is far below the 1.0
threshold. Per RESEARCH_LOOP.md Step 7, a decisive grid failure like this
does not warrant spending additional budget on the full single-config
validator suite (Sharpe/MDD/TC-survival/walk-forward/param-sensitivity) --
the grid result alone is conclusive. The paper's own microstructure-level
volatility-spillover finding (statistically significant on 1-minute bars)
does not translate into an exploitable DAILY-bar trend-following gate;
likely explanation: the ~1-day-ahead volatility-spillover effect operates
on much shorter (intraday/1-min) timescales than this repo's daily-bar
strategy interface can capture, and/or a 2-3 day flat cooldown sacrifices
too much of ETH's trend-following upside to be worth avoiding a vol
expansion that a daily strategy is not very exposed to anyway.
