# Vervoort Zero-Lag Rainbow %B + Smoothed Stochastic confirmation

## Hypothesis
Sylvain Vervoort's "Smoothed Oscillator" (TASC Sep 2013, ported by LazyBear
on TradingView) builds a 10-stage "Rainbow" weighted moving average of
close, then a zero-lag EMA transform + TEMA smoothing to produce `tz`, whose
Bollinger-Band %B (`zlrbpercb`) is combined with a smoothed Stochastic of
`avg(rainbow, hlc3)` (`slowK`) as a two-oscillator confirmation system. Per
the source page, quoting Vervoort's own rules: "It must be bullish for a buy
signal... both oscillators must be moving up... Stoch crossing 50 is a good
confirmation signal." Operationalized: long entry when `zlrbpercb` crosses
above `entry_level` (0) while `slowK > stoch_confirm_level` (50); exit on
`zlrbpercb` crossing below `exit_level` (50) or `slowK` crossing below 50, or
a `max_hold_days` (10) time-stop.

Source: https://www.tradingview.com/script/EXtLf5PR-Indicator-Vervoort-Smoothed-Oscillator-LazyBear/
(Pine source code read directly in-browser; secondary reference
https://www.linnsoft.com/techind/vervoort for the underlying zero-lag TEMA
crossover concept).

## Grid test (Step 6)
`param_grid={"entry_level": [-20,-10,0], "stoch_confirm_level": [40,50]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 72, passed: 0, **pass_fraction: 0.0**
- by_asset_class: equity 0/36, crypto 0/36
- by_vol_regime: low 0/24, mid 0/24, high 0/24
- best_cell: entry_level=-20, stoch_confirm_level=40, QQQ, mid-vol, Sharpe 0.50 (still below the 1.0 threshold)
- worst_cell: entry_level=0, stoch_confirm_level=50, SPY, mid-vol, Sharpe -1.42

The default single-config test (entry_level=0, stoch_confirm_level=50) on
QQQ 2019-2026 produced only 3 trades over 7.7 years (total return -6.7%),
confirming the grid finding: the two-oscillator confirmation gate is far too
restrictive (`slowK>50` combined with a `zlrbpercb` zero-cross rarely
co-occur cleanly), producing too few trades for a meaningful edge, and the
few that do trigger tend to be losers.

## Decision: REJECT
Decisive 0/72 grid pass fraction across both asset classes and all
volatility regimes. No single-config validator suite run given the grid is
uniformly decisive (per Step 7 guidance, a 0-pass grid does not warrant
spending budget on a full single-config validator pass).

## Notes
- Distinct from other Stochastic/%B strategies already tested (classic BB
  %B mean reversion, Fisher-Transform-of-Stochastic, Inverse-Fisher-
  Transform-of-Stochastic) since this uses a bespoke 10-stage zero-lag
  "Rainbow" MA plus a two-oscillator AND-gate confirmation, not a single
  oscillator crossover.
- Strategy file kept in `strategies/` as a rejected-attempt record (see
  knowledge_base entry), not a live strategy.
