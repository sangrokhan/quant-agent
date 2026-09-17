# Backtest Report: F. Arden Thomas Voting With Multiple Timeframes (Stochastic Vote)

**Strategy file:** `strategies/2026-09-17_multitf_stochastic_voting.py`
**Source:** Traders.com Nov 2020 Traders' Tips (F. Arden Thomas, "Voting With
Multiple Timeframes", TASC Aug 2020 article / Nov 2020 Traders' Tips code),
TradeStation EasyLanguage code, read via `browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2020/11/TradersTips.html`.

## Hypothesis

Compute a stochastic oscillator independently across 7 timeframes (daily +
6 subsampled intervals: 5/10/15/21/31/63 trading days), then count how many
agree the market is oversold (BuyPressure) or overbought (SellPressure).
Broad multi-timeframe agreement should be a stronger reversal signal than
any single-timeframe reading. Genuinely novel N=7-timeframe voting
mechanic, distinct from this repo's existing 2-3-timeframe strict-alignment
strategies.

## Grid test (Step 6)

`stoch_length` in [7,10,14] x `buy_threshold` in [4,5,6] x `max_hold_days`
in [15,20,30], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01..2026-09-01. 324 cells total.

- **pass_fraction: 0.231** (75/324)
- by_asset_class: equity 30/162 (0.185), crypto 45/162 (0.278)
- by_vol_regime: low 45/108 (0.417), **mid 0/108 (0.0)**, high 30/108
  (0.278) -- the mid-vol tercile passed ZERO cells across the entire grid,
  a decisive structural weakness: whatever regime characterizes "mid"
  volatility periods (transitional/choppy markets) breaks this
  multi-timeframe voting signal completely.
- No cell passed all 3 vol-regime terciles for any symbol.

## Single-config validation attempts (Step 7)

Extensive hand-search around the grid neighborhood (both equity symbols
across `stoch_length` in [3,5,7,10,14], `buy_threshold` in [3,4,5,6],
`max_hold_days` in [15,20,30]) failed to find a full-sample config that
both (a) clears Sharpe >= 1.0 and (b) has a meaningful trade count (>=10
trades over 7.5 years). Configs with enough trades (13-69) topped out at
Sharpe ~0.72; configs reaching Sharpe >1.0 had only 2 trades (statistically
meaningless). Crypto full-sample search likewise found no cell reaching
Sharpe 1.0 with an adequate trade count within the grid's parameter
neighborhood (best grid cells were low-vol-only artifacts, per the
`by_vol_regime` breakdown above -- mid-vol failed universally).

**No validator suite was run** since no candidate config survived the
initial Sharpe/trade-count screen -- consistent with RESEARCH_LOOP.md's
guidance that a rejection can be logged directly from grid-test evidence
when nothing promising survives.

## Overall decision

**REJECTED across all asset classes.** The mid-vol-regime universal failure
(0/108 grid cells) is the most decisive evidence: this multi-timeframe
voting mechanic appears to only produce tradeable signals in the two
extreme volatility terciles (calm trending markets, or crisis/high-vol
markets), not in normal/transitional conditions -- and even within those
favorable regimes, no full-sample config combined adequate trade frequency
with Sharpe >= 1.0. The core "many independent timeframes voting" idea,
while conceptually interesting, does not translate into an accepted
strategy with this repo's implementation and thresholds.
