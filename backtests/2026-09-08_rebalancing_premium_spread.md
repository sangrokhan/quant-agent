# Backtest Report: Rebalancing-Premium Long-Short Spread (2-asset adaptation)

**Strategy file:** `strategies/2026-09-08_rebalancing_premium_spread.py`
**Outcome:** REJECTED (decisive, both asset classes)

## Hypothesis

Per Quantpedia "Rebalancing Premium in Cryptocurrencies"
(https://quantpedia.com/strategies/rebalancing-premium-in-cryptocurrencies/,
paper: Hanicova/Vojtko SSRN 3982120): a daily-rebalanced equal-weight
portfolio of volatile/uncorrelated assets earns a structural "rebalancing
premium" over a buy-and-hold (weight-drift) version of the same portfolio.
Source strategy: long a daily-rebalanced 27-crypto equal-weight portfolio,
short (70% weight) a buy-and-hold version of the same 27-crypto basket,
reporting Sharpe 2.93 (2018-2021, small starting-capital-fraction
assumption -- their own MDD figure of -99.99% at that assumed capital
fraction is a leverage artifact, not a literal statement about the
strategy).

We adapted this down to the minimal 2-asset version fitting this repo's
single-primary-asset contract: pair the primary with TLT (equity primaries)
or a second major crypto (ETH for BTC primary), form the daily-rebalanced
50/50 vs buy-and-hold weight-drift portfolios internally, and go long the
spread (rebalanced - short_weight * buy-hold).

## Grid summary

Equity grid: `short_weight` in [0.5, 0.7, 0.9], QQQ/SPY paired with TLT,
3 vol-regime terciles = 18 cells. **pass_fraction: 0.056** (1/18, in the
mid-vol tercile only, Sharpe 1.089 -- a single marginal pass, not a
pattern).

Crypto grid: `short_weight` in [0.5, 0.7, 0.9], BTC/USDT paired with
ETH/USDT, 3 vol-regime terciles = 9 cells. **pass_fraction: 0.0** (0/9) --
decisive reject; best cell only Sharpe 0.564 (low-vol, short_weight=0.9).

## Full-sample validators (best-looking configs)

| Config | Sharpe | MDD | Passed |
|---|---|---|---|
| QQQ/TLT, short_weight=0.7 | -0.080 | 0.198 | FAIL (negative Sharpe) |
| BTC/ETH, short_weight=0.9 | 0.224 | 0.129 | FAIL |

## Decision: REJECTED

The 2-asset adaptation of the rebalancing-premium construction does not
reproduce anything close to the source's reported edge in either asset
class. Two likely reasons, worth noting for a future loop considering this
angle again: (1) the source's edge comes from a 27-asset basket -- more
constituent pairs generate more rebalancing opportunities and the
diversification-return effect scales with basket size/dispersion, so a
2-asset pair may be structurally too thin to harvest a meaningful premium;
(2) TLT/QQQ and BTC/ETH are both MORE correlated pairs than the source's
diverse 27-crypto basket (which explicitly spans very different
altcoin/majors dispersion), and the rebalancing premium is theoretically
larger for genuinely uncorrelated/high-dispersion pairs. A future
iteration could test a wider multi-asset basket version (e.g. 5-10 equal
sector/crypto legs) if revisiting this idea, rather than the minimal
2-asset construction tested here.
