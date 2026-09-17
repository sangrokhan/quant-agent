# Backtest Report: DMI Stochastic Reversal (TASC Jan 2013, Barbara Star)

**Strategy file:** `strategies/2026-09-17_dmi_stochastic_reversal.py`
**Source:** http://traders.com/documentation/feedbk_docs/2013/01/traderstips.html
(TASC January 2013 Traders' Tips, "The DMI Stochastic" by Barbara Star, PhD;
read this iteration via `browser_exec` after `web_search` produced no usable
DDGS results and `web_extract` errored — a normal fallback path, not an
error condition).

## Hypothesis

The DMI Oscillator (`+DI(n) - -DI(n)`, Wilder's directional indicators) gives
trend direction; a stochastic-style percent-rank normalization of the DMI
Oscillator over a short lookback (`DMIStoch = 100 * Sum(DMIOsc-LowestOsc,
sum_period) / Sum(HighestOsc-LowestOsc, sum_period)`) flags reversal points
in the oscillator itself. Long when `DMIOsc > 0` (bullish direction) AND
`DMIStoch` crosses above its own short SMA; exit on trend flip or reversal
signal fading. This is a previously-untested construction distinct from the
repo's 20+ prior ADX/DMI crossover/threshold entries — none apply a
stochastic normalization to the oscillator series itself.

## Grid test summary (Step 6)

`param_grid={"dmi_length": [10,14,20], "sum_period": [3,5]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 72, **passed_cells:** 26, **pass_fraction:** 0.361
- **by_asset_class:** equity 17/36 (0.47), crypto 9/36 (0.25)
- **by_vol_regime:** low 16/24 (0.67), mid 8/24 (0.33), high 2/24 (0.08)
- **best_cell:** dmi_length=14, sum_period=3, QQQ, low-vol regime, Sharpe=3.22
- **worst_cell:** dmi_length=20, sum_period=3, QQQ, high-vol regime, Sharpe=-0.74

Holds up mainly in low-vol regimes; degrades sharply in high-vol regimes
across both asset classes (2/24 pass) — a narrow, regime-dependent edge even
before transaction costs.

## Single-config validators (Step 7) — best grid config: dmi_length=14, hl_period=3, sum_period=3, ma_period=3

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.37 | **FAIL** 0.67 |
| Max Drawdown (<=0.25) | PASS 0.151 | PASS 0.124 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **FAIL** 0.378 (340 trades) | **FAIL** -0.103 (354 trades) |
| Walk-forward (manual 4-way contiguous split, >=75% pass, `check_walk_forward`'s vectorbt `RangeSplitter` API absent in installed vectorbt version — manual fallback used per repo convention, e.g. `backtests/2026-09-06_elder_safezone_trailing_stop.md`) | PASS 1.0 (4/4) | PASS 0.75 (3/4) |
| Parameter sensitivity (relative std <=0.5, 6-cell dmi_length x sum_period sweep) | PASS 0.225 | PASS 0.366 |

## Decision: REJECT

The strategy's reversal signal fires too frequently (~340-354 entries/exits
over the ~7.5-year sample on both QQQ and SPY) for the 10bps/trade
transaction-cost assumption — net-of-cost Sharpe fails on both symbols despite
gross Sharpe passing on QQQ. SPY additionally fails the raw gross-Sharpe
threshold. The grid test corroborates this: performance is concentrated in
low-vol regimes (0.67 pass fraction) and collapses in high-vol regimes (0.08)
and on crypto (0.25) — a narrow, cost-fragile edge, not a broad one. Crypto
not evaluated further given the equity-level TC failure already disqualifies
the primary config.
