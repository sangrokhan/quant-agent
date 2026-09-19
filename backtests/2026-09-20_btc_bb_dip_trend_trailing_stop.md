# BTC Bollinger-Band dip-buy + trend filter + ATR trailing stop — REJECTED

**Hypothesis source:** CoinQuant's "Does Buying the Dip Work in Crypto? 9
Years of Backtested Evidence"
(https://www.coinquant.ai/blog/does-buying-the-dip-work-in-crypto-9-years-of-backtested-evidence,
read via `browser_exec`). CoinQuant's own disclosed naive BTC dip-buy
backtest (BB(20,2) dip entry, mean-reversion exit at the middle band) LOST
money (-13.0%) despite a 63.2% win rate, missing BTC's +714.1% buy-and-hold
return. Source's own explicitly suggested fixes: add a longer-term trend
filter to only buy dips in an uptrend, and replace the mean-reversion exit
with a trailing stop so recoveries-turned-trends aren't cut short. This
iteration directly implements both suggested fixes (SMA(200) trend filter
+ ATR-based ratcheting trailing stop) as a genuinely new combination not
previously tested in this repo.

## Grid test (Step 6)

`atr_mult ∈ {2.0, 3.0, 4.0} × trend_window ∈ {150, 200}`, symbols =
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3, 72
total cells.

- **pass_fraction: 0.014** (1/72 cells passed) — near-total failure
- **by_asset_class:** equity 1/36, **crypto 0/36** (decisive failure on
  the source's own primary asset)
- **by_vol_regime:** low 1/24, mid 0/24, high 0/24

## Single-config validation (Step 7) — BTC/USDT, atr_mult=3.0, trend_window=200

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period 2019-2026) | 0.133 | ≥ 1.0 | **FAIL** (decisive) |
| Max drawdown | 0.389 | ≤ 0.25 | **FAIL** |
| Transaction-cost survival (10bps/trade, 694 trades) | net Sharpe 0.039 | ≥ 0.5 | **FAIL** (decisive) |

## Verdict: REJECTED

Despite directly implementing the source article's own diagnosed fixes
(trend filter + trailing stop), the resulting strategy still fails
decisively on BTC — and generated 694 trades over the sample (far more
than the source's naive 38-trade baseline), because the ATR trailing stop
combined with a relatively tight-band BB entry produces frequent
stop-outs/re-entries in choppy conditions rather than the intended
"let winners run" behavior. This suggests the trend filter (SMA 200) alone
does not adequately distinguish "dip within an uptrend" from "dip that's
actually a range-bound chop just above a rising long-term average" —
crypto's characteristic volatility clustering means price frequently
oscillates above/below the BB and ATR-stop levels within an overall
uptrend regime, generating repeated small losses from stop-outs that erode
the strategy via transaction costs (net Sharpe collapses from 0.133 to
0.039 after just 10bps/trade). A future revisit might need a wider/slower
trailing stop, a minimum-hold period before the trailing stop activates,
or an additional volatility-regime gate (as used successfully in several
other accepted strategies in this repo) rather than a trend filter alone.
