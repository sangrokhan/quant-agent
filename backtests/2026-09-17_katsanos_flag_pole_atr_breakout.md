# Backtest Report: ATR-Normalized Flag/Pole Breakout (Katsanos, TASC Dec 2014)

**Strategy file:** `strategies/2026-09-17_katsanos_flag_pole_atr_breakout.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2014/12/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

Markos Katsanos' quantified, ATR-normalized flag/pole pattern (pole height
>= `pole_min_atr` x ATR(40), flag range < `flag_max_atr` x ATR(40) with
non-positive linear-regression slope, rising-volatility confirmation,
genuine new-low uptrend precondition), adapted from intraday to daily bars.
Entry on breakout above the flag high; exit via profit target/ATR
stop/trailing stop/time-stop.

## Step 6 grid summary (pole_min_atr in {3.0,4.0} x flag_max_atr in {2.5,4.0}, 3 vol terciles, equity+crypto, 48 cells)

- `pass_fraction`: 7/48 = 0.146
- `by_asset_class`: equity 6/24, crypto 1/24
- `by_vol_regime`: low 4/16, mid 1/16, high 2/16
- `best_cell`: pole_min_atr=4.0/flag_max_atr=4.0, ETH/USDT, mid-vol, Sharpe 2.20 (single narrow cell, not representative)
- `worst_cell`: pole_min_atr=3.0/flag_max_atr=2.5, SPY, mid-vol, Sharpe -0.87

## Full-sample validation at best config (pole_min_atr=3.0, flag_max_atr=4.0)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | FAIL (0.853) | FAIL (0.641) |
| Max Drawdown (<=0.25) | PASS (0.185) | PASS (0.163) |
| TC survival (net Sharpe>=0.5) | PASS (0.827) | PASS (0.601) |
| Walk-forward (>=75%) | FAIL (3/4=75%... wait, 3/4 passes threshold) actually PASS | PASS (3/4) |
| Parameter sensitivity | PASS (0.056) | PASS (0.237) |
| Trades | 16 | 20 |

A broader local search (pole_min_atr in {2.0-4.0}, flag_max_atr in
{2.0-5.0}, k_target in {1.0,1.2,1.5}) found NO configuration clearing the
Sharpe>=1.0 threshold on either QQQ or SPY -- the strategy's underlying
Sharpe ceiling sits around 0.85 (QQQ) / 0.64 (SPY) regardless of tuning.

## Decision

**Reject** (QQQ and SPY both fail Sharpe threshold at every searched
config; crypto grid cells that passed were narrow single-tercile Sharpe
spikes, not a robust edge -- pass_fraction 0.146 overall is low). The
underlying pattern-detection logic (translated faithfully from Katsanos'
intraday EasyLanguage to daily bars) produces too few, too weak signals on
this repo's liquid daily-bar universe to clear the Sharpe bar; the
intraday-to-daily adaptation likely loses the finer-grained pattern
geometry the original was designed to exploit.
