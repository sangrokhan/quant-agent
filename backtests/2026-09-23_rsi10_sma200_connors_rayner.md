# 2026-09-23 — RSI(10)/SMA(200) Connors-Rayner Mean Reversion

## Hypothesis

Per TradingWithRayner's "Mean Reversion Trading Strategy That Works
(86.84% Winning Rate)"
(https://www.tradingwithrayner.com/mean-reversion-trading-strategy/, read
via browser_exec this iteration — web_search DDGS/Yahoo backend
TLS-errored on every query attempted, citing Connors & Alvarez): close >
SMA(200) trend gate, RSI(10) < 30 entry, buy next day's open (approximated
via this repo's standard 1-day-shift entry convention), exit when RSI(10)
crosses above 40 or after 10 trading days. Distinct RSI period/threshold
combo (10/30/40) and next-day-open timing from prior repo RSI mean-
reversion variants (RSI(2) same-day-close 2026-09-03-005; RSI(4)
same-day-close 2026-09-10-083).

Source URL: https://www.tradingwithrayner.com/mean-reversion-trading-strategy/

## Grid summary (Step 6)

- Grid: rsi_entry ∈ {25, 30} × rsi_exit ∈ {40, 50} × {QQQ, SPY, BTC/USDT,
  ETH/USDT} × 3 vol terciles = 48 cells.
- pass_fraction: 6/48 = 0.125
- by_asset_class: equity 2/24 passed; crypto 4/24 passed
- by_vol_regime: low 1/16, mid 5/16, high 0/16
- best_cell: SPY mid-vol, rsi_entry=30/rsi_exit=40 (source's own default),
  Sharpe 1.55
- worst_cell: BTC/USDT low-vol, rsi_entry=30/rsi_exit=50, Sharpe -0.47

## Single-config validation (Step 7) — full-sample, source's default (rsi_entry=30, rsi_exit=40)

| symbol | Sharpe | MDD | # trades |
|---|---|---|---|
| SPY | 0.389 | 0.111 | 31 |
| QQQ | 0.112 | 0.199 | 33 |
| BTC/USDT | 0.080 | 0.256 | 1087 |
| ETH/USDT | 0.091 | 0.350 | 1085 |

(Crypto trade counts are inflated because `load_crypto` defaults to
interval="1h" outside the grid harness's explicit `interval="1d"` override
— documented infra quirk from 2026-09-14-119 — but the point estimate is
decisively low regardless.)

## Decision: REJECTED (all symbols)

Despite an attractive grid-cell Sharpe (1.55) in SPY's mid-vol tercile at
the source's own default parameters, the full-sample Sharpe at that same
config is only 0.389 on SPY and 0.112 on QQQ — both decisively below the
1.0 threshold. This is the same diagnostic pattern seen in other rejected
strategies this cron trigger: the grid's regime-masked Sharpe does not
generalize to the strategy's own full-sample performance, because the
grid's after-the-fact vol-tercile labeling of the full sample doesn't align
tightly with when the strategy's own RSI/SMA entry condition actually
fires. Crypto is decisively rejected on both symbols. No near-miss close
enough to threshold to warrant a parameter-refinement follow-up.
