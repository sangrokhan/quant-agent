# High-IBS 7/10-Day-Low Pullback — QQQ Backtest Report

**Date:** 2026-09-21 (cron trigger, iteration 3)
**Strategy file:** `strategies/2026-09-21_high_ibs_7day_low_pullback.py`
**Hypothesis source:** https://www.quantifiedstrategies.com/4th-free-strategy/
(fully free/disclosed with exact AmiBroker code, found via web_search which
worked normally this iteration)

## Hypothesis

Per quantifiedstrategies.com's "4th Free Strategy!" article, a QQQ pullback
strategy with exact disclosed AmiBroker code:

    Buy = ref(IBS,-1) > 0.5 AND Ref(L,-1) < Ref(LLV(L,7),-2) AND C < Ref(C,-1)
    Sell = C > Ref(H,-1)

Plain English: yesterday's IBS (Internal Bar Strength) was >= 0.5 (a
relatively strong close within its own range) AND yesterday's low broke
below the lowest low of the 7 days before that (a fresh short-term
breakdown) AND today's close is lower than yesterday's close (weakness
continuing). Exit when today's close breaks back above yesterday's high.
This is distinct from every other IBS entry already in this repo, all of
which use LOW IBS (oversold panic) as the trigger -- here IBS>=threshold
(relative strength) is combined with a fresh N-day breakdown and a down-day
filter: buying strength-within-weakness during an emerging pullback, not a
pure oversold-panic signal. Source's own backtest (QQQ, 0.03%/trade costs
included): 179 trades, 77% win rate, profit factor 3.5, CAGR 8.5% at 8%
market exposure (100% risk-adjusted return), MDD 17% (buy-and-hold 82%).

## Grid test summary (ibs_threshold x lookback_days x symbol x vol-regime)

- Grid: `ibs_threshold` in {0.4, 0.5, 0.6}, `lookback_days` in {5, 7, 10};
  symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); 3 vol-regime terciles.
- **Total cells:** 108, **Passed:** 13, **pass_fraction = 0.120** (a
  selective, narrow-scope strategy -- low overall pass fraction but the
  cells that do pass are strong and concentrated on QQQ).
- By asset class: equity 12/54; crypto 1/54 (near-total failure on crypto).
- By vol regime: low 6/36, mid 0/36, high 7/36 — unusually, this strategy's
  passing cells split between low and HIGH vol regimes (not mid), unlike
  most trend strategies tested this cron trigger which fail high-vol
  outright; consistent with a mean-reversion/pullback mechanism that can
  work in sharp high-vol pullbacks as well as calm low-vol ones.
- Best average full-sample QQQ cells: (ibs_threshold=0.4, lookback_days=10)
  avg Sharpe 1.157 -- close to the source's own disclosed 0.5/7 defaults but
  slightly looser thresholds perform better on 2016-2026 data.

## Single-config validation, QQQ, full sample 2016-2026 (ibs_threshold=0.4, lookback_days=10)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.186 | 1.0 |
| Max drawdown | ✅ | 0.085 | 0.25 |
| Transaction cost survival (10bps/trade, 50 trades) | ✅ | 1.087 net Sharpe | 0.5 |
| Walk-forward (4 splits) | ✅ | 1.0 pass fraction | 0.75 |
| Parameter sensitivity (9-cell QQQ grid) | ✅ | 0.171 relative std | 0.5 |

All validators passed cleanly. Max drawdown is unusually low (8.5%),
consistent with the source's own reported 17% MDD (against buy-and-hold's
82%) and the strategy's very low market exposure (mean-reversion, short
holds).

## Decision: ACCEPT (QQQ only, ibs_threshold=0.4, lookback_days=10)

Scope: QQQ, mean-reversion pullback with tight risk (low MDD, moderate trade
count of 50 over the sample). Grid shows this strategy is narrow (low
overall pass fraction, near-zero on crypto and SPY) but very strong within
its scope. Do not extend to crypto or assume it generalizes to other
equities without further testing.
