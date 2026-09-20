# 2026-09-20: Awesome Oscillator Trendline Cross — REJECTED

**Hypothesis:** Per https://www.tradingsim.com/blog/awesome-oscillator
("Bonus Strategy", the source's own novel unpublished idea): rather than
waiting for a Bill Williams Awesome Oscillator (AO=SMA(median,5)-
SMA(median,34)) zero-line cross, draw a trendline connecting two
successive AO swing highs while AO is still above zero; go short the
moment AO breaks below that (typically downward-sloping) trendline --
earlier than the zero-cross itself. Bullish is the exact mirror below
zero. Adapted to a systematic daily-bar rule using a confirmed-fractal
swing-point detector and a linear trendline projected forward bar-by-bar.

**Source:** https://www.tradingsim.com/blog/awesome-oscillator
(browser_exec).

**Grid test** (pivot_strength in [2,3,5], max_hold_days in [10,20,30],
QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles, 108 cells):
- **pass_fraction: 0.0** (0/108) -- decisively zero, despite one cell
  (ETH/USDT low-vol, pivot_strength=2/max_hold_days=30) showing Sharpe
  1.28 on its own (MDD must fail there too, since 0/108 cells clear both
  thresholds).
- worst_cell: SPY mid-vol, sharpe -1.39

**Full-sample confirmation** at the grid's most-promising config
(pivot_strength=2, max_hold_days=30):

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | -0.603 (FAIL) | 0.497 (FAIL) |
| SPY | 0.145 (FAIL) | 0.374 (FAIL) |
| BTC/USDT | -0.238 (FAIL) | 0.670 (FAIL) |
| ETH/USDT | -0.027 (FAIL) | 0.870 (FAIL) |

All 4 symbols fail BOTH Sharpe and MDD decisively at full sample --
negative or near-zero Sharpe on 3 of 4, and catastrophic drawdowns
(37-87%) on all 4.

**Decision: REJECTED.** Grid pass_fraction is 0.0 across all 108
cells -- a fully decisive rejection. Full-sample confirms the failure is
not a scoping/tercile artifact: every symbol fails both primary
validators. The always-re-entering, trendline-projection design likely
produces frequent false breaks (a straight line drawn through only 2
points and projected indefinitely forward will diverge from AO's actual
bounded oscillation quickly), consistent with the source's own caveat
that this was an untested, "bonus" idea offered without a rigorous
backtest. Walk-forward/param-sensitivity/tx-cost validators skipped given
the decisive 0.0 grid pass_fraction.

Strategy file (`strategies/2026-09-20_ao_trendline_cross.py`) kept as a
record of a rejected attempt — not live.
