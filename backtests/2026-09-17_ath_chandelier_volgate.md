# All-Time-High + ATR Chandelier Trailing Stop, Low/Mid-Vol Regime Gated

**Strategy file:** `strategies/2026-09-17_ath_chandelier_volgate.py`
**Source / hypothesis basis:** Direct follow-up to near-miss
`2026-09-04-025` (per QuantPedia/Wilcox & Crittenden, "Does Trend Following
Work on Stocks?", https://quantpedia.com/strategies/trend-following-effect-in-stocks/).

## Hypothesis

The original all-time-high breakout + ATR(10) chandelier trailing-stop
strategy missed the Sharpe 1.0 threshold on QQQ by only 3.4% (0.966) while
passing every other validator, and its own grid breakdown showed the edge
concentrated almost entirely in the low-vol tercile (12/24 passing cells)
vs 2/24 mid-vol and 0/24 high-vol. This iteration tests whether gating new
entries out of the high-vol regime (20d realized vol vs its trailing 252d
median) recovers the missing Sharpe.

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: atr_multiplier in {2.5, 3.0, 4.0}, vol_regime_ratio in {0.9, 1.0, 1.2}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3 (low/mid/high realized-vol terciles), 2018-01-01 to 2026-09-01
- 108 total cells, 18 passed -> **pass_fraction = 0.167**
- By asset class: equity 18/54, crypto 0/54 (crypto decisively rejected, as in the base strategy)
- By vol regime: low 18/36, mid 0/36, high 0/36
- Best cell: SPY, atr_multiplier=4.0, vol_regime_ratio=0.9, low-vol tercile, Sharpe=2.10
- Worst cell: SPY, atr_multiplier=3.0, vol_regime_ratio=0.9, mid-vol tercile, Sharpe=-1.47

## Single-config validation (best config: atr_multiplier=4.0, vol_regime_ratio=0.9)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** 0.445 | **FAIL** 0.343 |
| Max drawdown (<=0.25) | pass 0.233 | pass 0.190 |
| TC survival (net Sharpe >=0.5) | **FAIL** 0.429 | **FAIL** 0.321 |
| Walk-forward (>=0.75 splits positive) | pass 0.75 (3/4) | pass 0.75 (3/4) |
| Parameter sensitivity (rel std <=0.5) | pass 0.126 | pass 0.336 |

## Verdict: REJECTED

The regime gate did NOT fix the base strategy's near-miss -- it made it
substantially **worse** on full-sample Sharpe (QQQ 0.445 vs the ungated
strategy's 0.966; SPY 0.343). The grid's per-regime cells look excellent
(low-vol Sharpe up to 2.10) but the full-sample blended result collapses,
because: (1) suppressing entries during high/mid-vol regimes also removes
some of the strategy's *best* individual trades (all-time-high breakouts
that happen to occur just as vol is elevated are not necessarily bad
trades -- vol level at entry doesn't reliably predict this specific
signal's outcome), and (2) with only 13-14 trades total over 8+ years, the
regime gate meaningfully cuts an already-small sample, amplifying variance.

**Lesson for future loops:** the "gate entries out of the bad regime" fix
pattern that has worked for high-frequency mean-reversion strategies in
this repo does NOT generalize to a very-low-frequency signal like this one
(all-time-high breakouts happen a handful of times per instrument per
decade) -- removing even 2-3 of those handful of trades can flip the
full-sample Sharpe. The original near-miss (2026-09-04-025) remains the
better-documented near-miss to revisit with a different remedy (e.g.
atr_multiplier=4.0 unconditionally, or a longer sample/different equity
symbol), not a vol regime gate.
