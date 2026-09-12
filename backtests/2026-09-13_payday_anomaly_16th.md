# Payday Anomaly (16th-of-month hold)

Hypothesis: Ma & Pratt (SSRN 3257064), via Quantpedia
https://quantpedia.com/strategies/payday-anomaly/ -- mid-month semi-monthly
paycheck (15th) drives retirement-contribution inflows into broad-market
funds the following day; source finds the 16th calendar day of the month is
the 3rd-best day of the month for S&P 500 returns (1980-2010 sample,
indicative Sharpe 0.6, CAGR 2.57%). Distinct from every turn-of-month
strategy in this repo (all anchor to trading-day COUNT, not calendar-day
date).

## Single-config results (window_start_day=16, window_end_day=16)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | -0.135 (fail) | 0.143 (pass) |
| SPY | -0.241 (fail) | 0.136 (pass) |

## Grid summary (window_start_day x window_end_day, equity+crypto, 3 vol terciles)

pass_fraction: 0.0/48 (decisive fail across every cell)
by_asset_class: equity 0/24, crypto 0/24
by_vol_regime: low 0/16, mid 0/16, high 0/16
best_cell: QQQ high-vol Sharpe=0.574 (still below 1.0 threshold)
worst_cell: SPY low-vol Sharpe=-1.839

## Verdict: REJECTED (decisive)

Full-sample Sharpe is NEGATIVE on both QQQ and SPY at the source's own exact
config (window=16-16), directly contradicting the source paper's 1980-2010
finding. Grid test across a small window-width sweep and both asset classes
confirms 0/48 pass -- no cell clears the Sharpe threshold. Plausible
explanation: source's own sample period (1980-2010) predates this repo's
test window (2019-2026); the effect may have decayed/been arbitraged away
in the post-2010 era.
