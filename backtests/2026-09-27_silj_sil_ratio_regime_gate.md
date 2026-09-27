# SILJ/SIL Ratio Regime Gate — rejected (near-miss)

**Hypothesis:** per
https://discoveryalert.com/education/silver-mining-equities-sil-silj-guide/,
junior silver miners (SILJ) carry substantially higher operating leverage
to silver-price moves than senior/large-cap silver miners (SIL). A rising
SILJ/SIL ratio (juniors outperforming seniors) proxies elevated risk
appetite, used as a regime gate on QQQ/SPY SMA trend-following -- extending
this repo's already-validated GDX/GLD ratio-gate pattern
(2026-09-11-049/065) one level further down the risk-appetite spectrum.
First SIL/SILJ strategy in this repo.

**Strategy file:** `strategies/2026-09-27_silj_sil_ratio_regime_gate.py`

## Grid test

`param_grid={trend_sma_window:[150,200,250], ratio_sma_window:[50,100,150]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2016-2026. pass_fraction 0.167 (18/108); equity 18/54, crypto 0/54
(decisive); by_vol_regime low 18/36, mid 0/36, high 0/36 (edge entirely
low-vol concentrated, same pattern as the GDX/GLD sibling strategy). Best
cell Sharpe 2.43 (SPY, trend_sma_window=250/ratio_sma_window=50, low-vol
tercile).

## Full-sample per-symbol tuning

A 35-combo local search (`trend_sma_window in [150..300] x ratio_sma_window
in [50,60,75,90,100,120,150]`) per symbol found:
- **QQQ best: Sharpe 0.968** (trend_sma_window=150, ratio_sma_window=75,
  MDD 14.3%)
- **SPY best: Sharpe 0.984** (trend_sma_window=225, ratio_sma_window=75,
  MDD 14.3%)

Both are razor-thin near-misses just under the 1.0 threshold. A shared
single config (maximizing min(Sharpe_QQQ, Sharpe_SPY)) only reaches 0.850
(trend_sma_window=200, ratio_sma_window=75) -- worse than either per-symbol
optimum, so no shared config clears the bar either.

## Outcome

**Rejected (near-miss)** — both QQQ (0.968) and SPY (0.984) fall just short
of the 1.0 Sharpe threshold at their individually best-tuned configs; no
shared config does better. Worth revisiting in a future iteration with a
different confirmation filter (e.g. combining with the sibling GDX/GLD gate
as a dual-metal-miner-leverage confirmation, or adding a volatility-regime
overlay per this repo's established near-miss-rescue pattern) given how
close both symbols already are to the bar.
