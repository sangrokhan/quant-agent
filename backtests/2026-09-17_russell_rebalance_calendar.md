# Russell 2000 (IWM) Annual Rebalancing Seasonal Effect

Hypothesis: per QuantifiedStrategies.com's "The Small-Cap Rally That Happens Once a Year"
(confirmed via Google search snippet this iteration, browser_exec fallback -- web_search
DDGS backend errored with TLS RequestError; full article paywalled beyond summary but exact
rule surfaced in the snippet): "Buy on the close of the first trading day after June 23rd.
Sell on the close of the first trading day of July." Exploits the Russell index annual
reconstitution (fourth Friday of June) creating predictable small-cap buy-side imbalances.
Mechanism-grounded calendar anomaly, distinct from every prior calendar effect tested in
this repo (turn-of-month, day-of-week, pre-holiday, Halloween indicator).

## Full-sample validation (2010-2026, single config, no grid needed -- rule has no tunable parameters)
| Symbol | Sharpe | MDD | TC-survival net Sharpe | trades |
|---|---|---|---|---|
| IWM (primary, per source) | 0.429 (fail) | 0.074 (pass) | 0.379 (fail) | 17 |
| QQQ (falsification) | 0.522 (fail) | 0.062 (pass) | 0.472 (fail) | 17 |
| SPY (falsification) | 0.667 (fail) | 0.053 (pass) | 0.594 (pass) | 17 |
| BTC/USDT (falsification) | 0.003 (fail) | -- | -- | -- |

## Decision
REJECTED across all symbols including IWM (the primary intended asset). Despite the source's
own reported strong backtest metrics (73% win rate, profit factor 3), this repo's full-sample
Sharpe calculation on the identical two-rule specification (once-yearly, ~5-8 day holding
period, 17 trades over 2010-2026) falls well short of the 1.0 threshold on all symbols. A
short annual holding period with only 17 observations produces a low-frequency, low-Sharpe
return stream by construction even with a genuinely positive average per-trade edge (the
source's own headline "risk-adjusted return" metric, CAGR/time-in-market, is not equivalent
to an annualized Sharpe ratio computed on daily strategy returns -- most days have zero
exposure so the ratio's denominator is dominated by near-zero-variance flat days, which
does not favorably compound into a standard Sharpe the way this repo's validator computes
it). This is consistent with several other single-trade-per-year calendar strategies
already rejected in this repo (Bitcoin halving 500-day rule, etc.) -- annual-frequency
anomalies with source-reported strong per-trade stats don't clear this repo's daily-return
Sharpe/MDD bar even when the underlying effect (index rebalancing flows) is real and
economically well-documented.
