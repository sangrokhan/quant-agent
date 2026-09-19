# Naive SMA Crossover with Hard Percentage Stop-Loss

**Hypothesis:** Per a Medium article by Kryptera, "I Found a 'Naive' Trend
Strategy on Reddit. I Backtested It on BTC and SOL."
(https://medium.com/@Kryptera/i-found-a-naive-trend-strategy-on-reddit-d02a831f4bf4),
a Reddit poster's viral claim: long when price crosses above SMA(20), exit
when it crosses back below, cap the damage with an 8% hard stop -- no
regime filter, no vol scaling. Reported triple-digit CAGRs on crypto with
a win rate under 40%. Tested here on this repo's own data across QQQ, SPY,
BTC/USDT, ETH/USDT for comparison (rather than trusting the Reddit
poster's original crypto-only claim).

## Strategy file
`strategies/2026-09-20_sma20_cross_hard_stop_naive.py`

## Grid test summary (sma_window in {10,20,30} x stop_pct in {0.05,0.08,0.12}, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-2026)

- pass_fraction: 0.361 (39/108 cells) -- one of the strongest grid results this cron trigger
- by_asset_class: equity 30/54, crypto 9/54 (crypto DOES pass some cells, unlike most strategies here, but far fewer than equity)
- by_vol_regime: low 27/36, mid 9/36, high 3/36

## Full-sample validators

### Crypto (source's own original claim) -- CONFIRMS source's own implied caveat

| Symbol | Config | Sharpe | MDD | TC net Sharpe |
|---|---|---|---|---|
| BTC/USDT | sma=20/stop=0.08 | 0.895 FAIL | 0.640 FAIL | 0.836 PASS |
| BTC/USDT | sma=30/stop=0.08 | 0.959 FAIL | 0.495 FAIL | 0.915 PASS |
| ETH/USDT | sma=20/stop=0.08 | 0.927 FAIL | 0.538 FAIL | 0.889 PASS |
| ETH/USDT | sma=30/stop=0.08 | 0.993 FAIL | 0.580 FAIL | 0.965 PASS |

None of the crypto configs clear this repo's Sharpe/MDD bar despite
decent-looking Sharpe (approaching 1.0) -- the drawdown is simply too
severe (49-64%) for an unfiltered hard-stop MA crossover on crypto,
consistent with the source article's own framing ("The Result Wasn't What
I Expected" when benchmarked against buy-and-hold).

### Equity -- ACCEPTED for QQQ

| Symbol | Config | Sharpe | MDD |
|---|---|---|---|
| QQQ | sma=30/stop=0.05 | **1.142 PASS** | **0.232 PASS** |
| QQQ | sma=20/stop=0.08 | 0.901 FAIL | 0.215 PASS |
| SPY | sma=30/stop=0.05 | 0.979 FAIL (near-miss) | 0.178 PASS |

QQQ at sma_window=30, stop_pct=0.05 (a tighter stop and longer MA than the
source's literal disclosed 20/8%) passes all 5 validators:

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.142 | >= 1.0 | PASS |
| Max drawdown | 0.232 | <= 0.25 | PASS |
| TC survival (10bps/trade, 84 trades) | net Sharpe 1.033 | >= 0.5 | PASS |
| Walk-forward (4 manual splits) | 4/4 positive (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (sma_window in {20,25,30,35} x stop_pct in {0.04,0.05,0.06,0.08}) | rel_std 0.088 | <= 0.5 | PASS |

Very low parameter sensitivity (0.088) -- this is a robust configuration,
not a lucky single cell.

## Outcome

**Accepted for QQQ only** (sma_window=30, stop_pct=0.05). SPY near-misses
at the same config (Sharpe 0.979). Crypto (BTC/USDT, ETH/USDT) rejected
decisively on MDD across every config tried -- the source's own original
claim (a hard 8% stop on a bare SMA(20) crossover "working" on crypto) is
NOT confirmed by this repo's independent test; the drawdown is simply too
severe for crypto's volatility. This nicely mirrors the source article's
own stated finding ("The Result Wasn't What I Expected" -- implying
disappointment once benchmarked properly).
