"""Backtest report: Glitch Index mean-reversion (2026-09-17).

Source: MQL5 CodeBase (https://www.mql5.com/en/code/20439, visited via
browser_exec -- web_search DDGS/Yahoo backend down with RequestError/TLS
errors on every query attempted this iteration), Mladen Rakic's MT5 port of
the "Glitch Index" originally from Active Trader magazine, February 2004.
First Glitch Index entry in this repo (0 prior KB hits).

Formula (fully disclosed by source):
    SMA=SMA(close,30); RocSMA=ROC(SMA,1)*0.1+1; SMAMult=SMA*RocSMA;
    Diff=Close-SMAMult; GlitchIndex=(Diff/Close)*100

Rule (source's own exact stated rule): long entry when GlitchIndex < -2 AND
highest GlitchIndex over trailing 30 bars < +5 (avoids buying into a
blow-off-top snap-back); exit when GlitchIndex > +2. Long-only, designed for
daily/weekly timeframes (source's own stated scope, matches this repo's
daily bars).

## Grid summary (sma_period in {20,30,45} x entry_threshold in {-1.5,-2.0,-3.0},
exit_threshold=2.0/blowoff_ceiling=5.0/lookback_bars=30/max_hold_days=40 fixed,
QQQ+SPY+BTC/USDT+ETH/USDT, vol_regime_splits=3)

- 108 cells total, 10 passed (9.3% pass_fraction) -- decisively weak across
  the entire grid
- by_asset_class: equity 7/54 (13.0%), crypto 3/54 (5.6%)
- by_vol_regime: low 2/36 (5.6%), mid 1/36 (2.8%), high 7/36 (19.4%)
- avg per-cell Sharpe across every (sma_period, entry_threshold) config
  ranges only 0.085-0.333 -- no config comes close to a respectable Sharpe,
  let alone the 1.0 threshold
- best cell: sma_period=30/entry_threshold=-1.5, SPY low-vol, Sharpe=1.35
  (isolated outlier, not representative of the broader grid)
- worst cell: sma_period=20/entry_threshold=-3.0, BTC/USDT low-vol, Sharpe=-0.78

## Decision: REJECT (no config, no asset class, no vol regime shows a
broadly viable signal -- decisive grid rejection, single-config validator
suite skipped since even the best full-grid-average config (avg Sharpe
0.333) is far below the 1.0 Sharpe threshold with no plausible fix path).

The "detrended SMA + rate-of-change-of-SMA multiplier" construction from
this 2004-era Active Trader system does not appear to produce a
statistically robust mean-reversion edge on modern QQQ/SPY/BTC/ETH daily
data at any tested parameterization -- consistent with many other
2000s-era discretionary-trading-magazine mean-reversion oscillators already
tested and rejected in this repo.
"""
