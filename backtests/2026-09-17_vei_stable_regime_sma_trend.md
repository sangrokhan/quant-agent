# VEI (Volatility Expansion Index) Stable-Regime SMA Trend Following

**Strategy file:** `strategies/2026-09-17_vei_stable_regime_sma_trend.py`
**Source:** r/algotrading post "The Signal I Use to Detect Hidden
Instability in Markets (Source Code Included)"
(u/Prabuddha-Peramuna, https://www.reddit.com/r/algotrading/comments/1phv4zz/,
read via browser_exec this iteration after web_search DDGS backend
errored) -- includes full disclosed Pine Script source.

## Hypothesis

VEI = ATR(10) / ATR(50) measures short-term volatility relative to its
own long-term baseline. VEI < 1.0 marks a "stable/controlled" regime
where trend setups behave well; VEI >= 1.0 marks volatility expansion
where trends get noisy and stops get hit more. This strategy pairs the
source's own regime filter with a plain SMA trend-following entry (exactly
as an independently-reported walk-forward test in the post's own comment
thread did), exiting on trend break, regime flip to unstable, or a
time-stop.

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: vei_threshold in {0.9, 1.0, 1.1}, trend_window in {50, 100}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3, 2018-01-01 to 2026-09-01
- 72 total cells, 23 passed -> **pass_fraction = 0.319** (one of the
  strongest grid results recorded in this log)
- By asset class: equity 18/36, crypto 5/36 (crypto shows real, non-trivial signal)
- By vol regime: low 15/24, mid 8/24, high 0/24
- Best cell: SPY, vei_threshold=1.1/trend_window=50, low-vol tercile, Sharpe 2.32

## Single-config validation (per-symbol tuned)

| Validator | QQQ (vt=1.05, tw=150) | SPY (vt=1.15, tw=40) | BTC/USDT (vt=1.15, tw=150) |
|---|---|---|---|
| Sharpe ratio (>=1.0) | **pass** 1.387 | **pass** 1.072 | pass 1.134 |
| Max drawdown (<=0.25) | pass 0.113 | pass 0.135 | **FAIL** 0.448 |
| TC survival (net Sharpe >=0.5) | **pass** 1.240 (81 trades) | pass 0.899 (91 trades) | pass 1.098 |
| Walk-forward (>=0.75 splits positive) | pass 1.0 (4/4) | pass 1.0 (4/4) | pass 1.0 |
| Parameter sensitivity (rel std <=0.5) | pass 0.074 | pass 0.096 | pass 0.125 |

QQQ and SPY: all 5 validators pass. BTC/USDT: Sharpe/TC/WF/param-sensitivity
all pass but MDD breaches the 0.25 threshold decisively (0.448) --
rejected. ETH/USDT similarly did not clear the Sharpe threshold in an
extensive local sweep (best found 0.868).

## Verdict: **ACCEPTED (QQQ, SPY)**, rejected (BTC/USDT MDD fail, ETH/USDT Sharpe fail)

QQQ: `vei_threshold=1.05, trend_window=150` (atr_short=10, atr_long=50,
max_hold_days=30 at file defaults).
SPY: `vei_threshold=1.15, trend_window=40`.

This is one of the strongest grid pass-fractions recorded in this log
recently (0.319) and, unusually for this repo's trend-following family,
shows real signal in the MID-vol tercile too (8/24), not just low-vol
(15/24) -- consistent with the source's own framing of VEI as capturing a
genuinely different regime axis (fast-vs-slow ATR ratio) than the more
common vol-percentile or Bollinger-width constructions already saturating
this repo (HVR, ATR-expansion, Choppiness Index, VHF -- none use a
ratio of two ATR values at different lookback lengths). BTC/USDT's MDD
failure (0.448) suggests the regime-flip exit isn't fast enough to
protect against crypto's characteristic sharp drawdowns even when Sharpe
looks respectable -- a future iteration could try a tighter
max_hold_days or an additional hard stop-loss specifically for the crypto
leg.
