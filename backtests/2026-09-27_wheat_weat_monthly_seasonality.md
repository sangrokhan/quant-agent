# Wheat (WEAT) Monthly Seasonality Calendar — rejected

**Hypothesis:** per https://forecaster.biz/seasonality/commodities/wheat/
(Wheat/KE monthly seasonality study, 5/7/10-year historical win-rate
backtest), wheat futures exhibit a repeating annual pattern -- bullish in
Feb-May and Aug-Sept-Nov, bearish in Dec-Jan/June-July/October. Long-only
adaptation: hold WEAT during the disclosed long-favored months, flat
otherwise. First grain-commodity seasonality strategy in this repo.

**Strategy file:** `strategies/2026-09-27_wheat_weat_monthly_seasonality.py`

## Results

Tested on WEAT (Wheat ETF), CORN, and SOYB (as a structural check across
related grain commodities), 2015-2026, with the source's exact disclosed
long-month set and two narrower sub-variants:

| Symbol | long_months=(2,3,4,5,8,9,11) [source's exact set] | (3,4,8,9) | (2,3,4,5) |
|---|---|---|---|
| WEAT | Sharpe -0.041 | 0.109 | 0.205 |
| CORN | Sharpe 0.203 | 0.524 | 0.048 |
| SOYB | Sharpe 0.312 | 0.230 | 0.122 |

WEAT's own full-sample MDD at the source's exact rule was 54.8% (in-market
58% of the time). No symbol/variant combination approaches the 1.0 Sharpe
threshold; the best result (CORN, narrowed to Mar/Apr/Aug/Sep) is still only
0.524.

## Outcome

**Rejected** — the source's disclosed calendar pattern (and reasonable
narrowings of it) does not produce a viable full-sample edge on any of the
three grain-ETF proxies tested (WEAT, CORN, SOYB); best Sharpe achieved was
0.524 (CORN), decisively below the 1.0 threshold. The underlying source
study's win-rate percentages describe average P&L per position over 5/7/10
years but evidently don't translate into a risk-adjusted (Sharpe) edge once
actually backtested against ETF total-return data.
