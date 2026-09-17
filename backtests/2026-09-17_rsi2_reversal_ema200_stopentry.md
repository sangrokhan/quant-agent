# Backtest Report: RSI(2) Setup + 2-Bar Down-Close Reversal + EMA200 Filter

**Strategy file:** `strategies/2026-09-17_rsi2_reversal_ema200_stopentry.py`
**Source:** https://traders.com/documentation/feedbk_docs/2014/05/traderstips.html
(TASC May 2014 Traders' Tips, "A Trading Method For The Long Haul" by
Donald W. Pendergast Jr., from the 2014 Bonus Issue of Stocks &
Commodities; TradeStation EasyLanguage credited to Doug McCrary/
TradeStation Securities; read this iteration via `browser_exec`).

## Hypothesis

Pendergast's system is a state machine: RSI(2)<5 arms a persistent
"RSISetUpOK" flag (not a same-bar check); the actual entry additionally
requires a 2-bar down-close reversal pattern (today's high < yesterday's
high AND both bars closed below their own opens) AND close above EMA(200);
entry is a stop order above the setup bar's high (approximated here as
same-daily-bar triggering since we only have daily OHLC, not intrabar
routing); exit via a 3-bar trailing low OR EMA(6) close-crossunder,
whichever hits first. Distinct from repo's existing RSI(2) variants
(simple threshold-cross/next-open entries) in the persistent-setup-flag +
reversal-pattern-confirmation + stop-entry + dual-exit combination.

## Grid test summary (Step 6)

`param_grid={"num_bars_for_trail": [3,5], "ema_filter_length": [150,200]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 48, **passed_cells:** 3, **pass_fraction:** 0.0625
- **by_asset_class:** equity 3/24 (0.125), crypto 0/24 (0.0)
- **by_vol_regime:** low 3/16, mid 0/16, high 0/16
- **best_cell:** num_bars_for_trail=3, ema_filter_length=150, SPY, low-vol regime, Sharpe=1.28
- **worst_cell:** num_bars_for_trail=3, ema_filter_length=150, ETH/USDT, high-vol regime, Sharpe=-1.31

## Single-config validators — grid-best config: num_bars_for_trail=3, ema_filter_length=150

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** -0.0002 | **FAIL** 0.131 |
| Max Drawdown (<=0.25) | PASS 0.142 | PASS 0.085 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **FAIL** -0.213 (62 trades) | **FAIL** -0.136 (62 trades) |

## Decision: REJECT

Both QQQ and SPY fail the primary Sharpe threshold by a wide margin (near
zero or barely positive), and net-of-cost Sharpe is decisively negative on
both given the moderate trade frequency (62 round trips over 7.5 years).
Max drawdown passes but that alone is insufficient. Grid pass_fraction of
0.0625 confirms this is not a parameter-tuning issue — the specific
2-bar-reversal-pattern + persistent-RSI-setup-flag construction does not
add value over the repo's simpler RSI(2) family on daily QQQ/SPY bars.
Crypto decisively rejected (0/24). Strategy file kept as a record of a
rejected attempt.
