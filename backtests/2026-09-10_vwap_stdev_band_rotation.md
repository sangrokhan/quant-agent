# 2026-09-10 — VWAP + 1st-Deviation-Band Rotation Setup (REJECTED)

## Hypothesis

Per https://www.trader-dale.com/simple-vwap-trading-strategies-your-guide-to-smarter-trades/
(Trader Dale): a rolling VWAP with volume-weighted 1st-deviation bands;
source's "Rotation Setup" for ranging markets — buy at the lower band, exit
at VWAP (the "magnet"), only in a non-trending (bands roughly horizontal)
regime. This implementation adapts the source's intraday-session VWAP to a
rolling N-day VWAP (no intraday session boundaries in this repo's daily
data) and approximates "horizontal bands" numerically as
band_width <= its own trailing median.

Strategy file: `strategies/2026-09-10_vwap_stdev_band_rotation.py`

## Grid summary (vwap_window in [10,20,40] x dev_mult in [1.0,1.5], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- 5/72 cells passed (pass_fraction 0.069), all 5 on equity — crypto 0/36 decisively.
- By vol regime: low 4/24, mid 0/24, high 1/24 — very narrow, mostly low-vol-only.
- Best cell: QQQ, vwap_window=20, dev_mult=1.0, low-vol tercile, Sharpe 1.63.
- Worst cell: SPY, vwap_window=40, dev_mult=1.5, mid-vol tercile, Sharpe -0.91.

## Full-sample quick check (vwap_window=20, dev_mult=1.0, 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) |
|---|---|---|---|
| QQQ | 0.321 (FAIL, thr 1.0) | 0.159 (pass) | 0.267 (FAIL, thr 0.5) |
| SPY | -0.109 (FAIL) | 0.267 (FAIL, thr 0.25) | -0.177 (FAIL) |

## Decision: REJECT

Decisive rejection on the full sample for both symbols — the grid's isolated
low-vol-tercile passes (Sharpe up to 1.63) do not generalize; full-sample
Sharpe collapses to 0.32 (QQQ) and -0.11 (SPY). This is consistent with a
strategy whose edge is a narrow-regime artifact rather than a robust effect.
The rolling-VWAP adaptation of an inherently intraday-session tool (VWAP
resets daily in the source's use case; here it's a smoothed 20-day rolling
proxy) likely loses the "fair value magnet" property the source describes,
since a rolling multi-day VWAP on daily bars behaves more like a slow SMA
with volume weighting than a true session VWAP. Not pursued further; no
crypto near-misses either (0/36 decisively). Full validator suite (walk-
forward, parameter sensitivity) skipped as unnecessary given the decisive
full-sample failure.
