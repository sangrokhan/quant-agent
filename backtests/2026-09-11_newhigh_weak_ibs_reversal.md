# 2026-09-11: New-High-But-Weak-Close (Donchian High + Low IBS) Contrarian Long (SPY)

**Strategy file:** `strategies/2026-09-11_newhigh_weak_ibs_reversal.py`
**Knowledge base id:** 2026-09-11-114

## Hypothesis

Per quantifiedstrategies.com's "5 Algorithmic Trading Strategies 2026"
(https://www.quantifiedstrategies.com/algorithmic-trading-strategies/,
"Strategy #5"): "Today's high must be higher than the high of the last ten
days, and the IBS indicator must be below 0.15. If both are true, we buy
the close... We sell when the close is higher than yesterday's high."
Source's own SPY backtest (1993-2026): 185 trades, ~8% time invested, 3.2%
annualized, only 8% max drawdown (their lowest-drawdown strategy of five
presented). This is genuinely distinct from every other IBS-family
strategy already in this repo — prior entries all condition on price
WEAKNESS (a new low / breakdown); here the price signal is a bullish new
N-day HIGH, but the close is contrarian-weak (near the day's low) despite
that — an intraday failed-follow-through pattern.

## Primary config (SPY)

`donchian_window=10, ibs_threshold=0.15, max_hold_days=20`, full sample
2019-01-01 to 2026-09-01.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.757 | ≥ 1.0 |
| Max drawdown | ✅ | 3.57% | ≤ 25% |
| Transaction cost survival (10bps/trade, 52 trades) | ✅ | net Sharpe 1.403 | ≥ 0.5 |
| Walk-forward (4 splits, manual date-slice fallback — vectorbt.utils.splitting API bug) | ✅ | 4/4 splits positive Sharpe (1.0) | ≥ 0.75 |
| Parameter sensitivity (ibs_threshold ∈ {0.1,0.15,0.2} × max_hold_days ∈ {10,20}, SPY) | ✅ | relative std 0.056 | ≤ 0.5 |

Strong, decisive pass on every validator — this is one of the cleaner
accepted strategies in the repo (very low drawdown, low trade frequency).

## Step 6 grid summary (donchian_window ∈ {10,20}, ibs_threshold ∈ {0.1,0.15,0.2}, max_hold_days=10; QQQ+SPY equity, BTC/USDT+ETH/USDT crypto; vol_regime_splits=3)

- Overall pass_fraction: 24/72 = **0.333**
- By asset class: equity 24/36 (0.667) — crypto **0/36 (0.0)**
- By vol regime: low 6/24 (0.25), mid 6/24 (0.25), high 12/24 (0.5)
- Best cell: SPY, high-vol, donchian_window=10/ibs_threshold=0.15/max_hold=10, Sharpe 2.38
- Worst cell: BTC/USDT, high-vol, donchian_window=20/ibs_threshold=0.15, Sharpe -0.10

**Honest scope:** equity only (QQQ, SPY) — crypto fails completely (0/36).
Unusually, this strategy's edge is CONCENTRATED in the **high-vol regime**
(12/24 pass) rather than the low-vol regime that most of this repo's
mean-reversion strategies favor — plausible since intraday failed-breakout
reversals are a higher-vol-regime phenomenon (sharp intraday moves that
fail to hold). Do not deploy on crypto.

## Decision: ACCEPT

All 5 validators passed decisively for the primary SPY config. Strategy
file and this report kept as a live accepted strategy, scoped to equity.

## Source

https://www.quantifiedstrategies.com/algorithmic-trading-strategies/
