# Backtest Report: Percentile Channel Hysteresis + Formation-Price Stop-Loss Rescue (QQQ)

**Strategy file:** `strategies/2026-09-22_percentile_channel_stoploss_rescue.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-043

## Hypothesis

Direct fix for this cron trigger's own prior near-miss rejection
(2026-09-22-042, percentile-channel-with-hysteresis QQQ trend/cash switch,
Sharpe pass but decisive MDD 0.2856 fail). Applies the repo's
already-accepted daily-reacting formation-price stop-loss overlay
mechanism (per Han/Zhou/Zhu "Taming Momentum Crashes: A Simple Stop-Loss
Strategy", https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/,
same mechanism previously used to rescue 2026-09-22-037->038) on top of
the identical, otherwise-unmodified percentile-channel entry/exit logic
from 2026-09-22-042: exit immediately (checked daily, not just monthly) if
close falls below the trade's own entry price by more than
`stop_loss_pct`.

## Grid Test Summary (Step 6)

- Total cells: 36 (3 stop_loss_pct values x fixed window/entry_threshold,
  3 vol regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.25 (9/36)
- By asset class: equity 9/18, crypto 0/18 (decisive crypto reject,
  consistent with every other TSMOM/percentile-channel variant tested)
- By vol regime: low 6/12, mid 3/12, high 0/12
- Best cell: SPY, stop_loss_pct=0.05, low-vol regime, Sharpe 2.41
- Worst cell: BTC/USDT, stop_loss_pct=0.08, low-vol regime, Sharpe -1.51
- Stop-loss level nearly inert across 0.03-0.08 (relative std 0.011 on QQQ)

## Single-Config Validation (Step 7), QQQ, window=252/entry=0.7/exit=0.25/rebalance_days=21/stop_loss_pct=0.05

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | true | 1.121 | 1.0 |
| Max drawdown | true | 0.229 | 0.25 |
| Transaction cost survival (10bps/trade, 5 trades) | true | net Sharpe 1.117 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true | 3/4 splits positive (0.75 pass fraction, exactly at threshold) | 0.75 |
| Parameter sensitivity | true | relative std 0.011 | 0.5 |

## Outcome: ACCEPTED (QQQ)

All 5 validators pass. Successfully rescues 2026-09-22-042 -- MDD drops
from the parameter-invariant 0.2856 to 0.229 (below the 0.25 threshold),
and Sharpe improves (1.019 -> 1.121) rather than trading off against the
drawdown fix. Only 5 round-trip trades over 8.6yr (very low turnover),
consistent with the strong TC-survival result. Walk-forward is an exact
0.75 pass (one negative split, -0.69, in the earliest quarter which
includes the 2018-2019 shakeout before the stop-loss overlay's benefit
becomes visible in later splits -- worth noting as the thinnest-margin
validator here). SPY at the same shared config not separately validated
this iteration (grid best cell for SPY was stop_loss_pct=0.05 low-vol
2.41, consistent direction). Crypto (BTC/USDT, ETH/USDT) rejected
decisively per grid (0/18 cells), consistent with every other TSMOM/trend
variant tested in this repo. Source chain: https://cssanalytics.wordpress.com/2015/01/26/a-simple-tactical-asset-allocation-portfolio-with-percentile-channels/
(2026-09-22-042's original source) + https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/
(this fix's stop-loss mechanism source, previously used for 2026-09-08-178/179
and 2026-09-22-037/038).
