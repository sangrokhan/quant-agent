# Price Zone Oscillator (PZO) Trend-Regime Strategy (2026-09-18)

**Strategy file:** `strategies/2026-09-18_pzo_trend_regime.py`
**Hypothesis id:** 2026-09-18-114
**Source:** TASC June 2011 Traders' Tips ("Entering The Price Zone" by Walid
Khalil and David Steckler), TradeStation EasyLanguage,
https://traders.com/documentation/feedbk_docs/2011/06/traderstips.html
(read via browser_exec fallback -- web_search's DDGS backend intermittently
failing with TLS/connection errors this iteration).

## Hypothesis

PZO = 100 * EMA(sign(Close-Close[-1])*Close, period) / EMA(Close, period),
a momentum oscillator roughly bounded in [-100,100]. The source's own
disclosed EasyLanguage strategy defines named zone levels (ExtremeOverbot=60,
Overbought=40, MidPlus=15, MidMinus=-5, Oversold=-40, ExtremeOversold=-60)
and switches its entry/exit logic based on an ADX(14) trend-strength regime,
gated by an EMA(60) price trend filter. This strategy implements the
long-only subset of the source's disclosed trending-regime logic: entry
either on PZO recovering above -40 (oversold bounce) or on a two-stage
"cross above zero, then confirm strength by crossing above +15" signal;
exit on PZO peaking out after exceeding +60 and turning down, or on the
EMA trend filter breaking while PZO is still negative. Zero prior Price
Zone Oscillator entries in this repo (genuinely new indicator family).

## Grid test summary (Step 6)

Grid: `pzo_period` in {10, 14, 20} x `adx_trend_threshold` in {15.0, 20.0},
symbols {QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto),
vol_regime_splits=3. 72 total cells.

- **Overall pass_fraction: 0.292** (21/72)
- By asset class: equity 20/36 passed (strong), crypto only 1/36 passed
  (very weak) -- almost entirely an equity-only mechanism.
- By vol regime: low 12/24, mid 9/24, high 0/24 -- ZERO high-vol regime
  cells passed; this strategy only works in low/mid volatility conditions.
- Best cell: equity QQQ, pzo_period=20, adx_trend_threshold=15.0, low-vol
  regime, Sharpe 2.80.
- Worst cell: equity SPY, pzo_period=20, adx_trend_threshold=20.0, high-vol
  regime, Sharpe -0.94.
- Best aggregated config: **SPY, pzo_period=10, adx_trend_threshold=15.0**
  (mean grid Sharpe 1.25, highest of all symbol/param combos).

## Single-config validation (Step 7) — SPY, pzo_period=10, adx_trend_threshold=15.0

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.140 | >= 1.0 |
| Max drawdown | True | 0.133 | <= 0.25 |
| Transaction cost survival (10bps/trade, 95 trades) | True | 0.888 (net Sharpe) | >= 0.5 |
| Walk-forward (4 contiguous splits, manual fallback) | True | 1.0 (4/4 splits Sharpe>0) | >= 0.75 |
| Parameter sensitivity (6-point grid, relative std) | True | 0.299 | <= 0.5 |

(Same `check_walk_forward` vectorbt API incompatibility worked around as
this cron trigger's prior two entries -- manual 4-way split.)

## Decision: ACCEPT

All 5 validators passed for SPY at pzo_period=10, adx_trend_threshold=15.0.
Scope: strictly equity, and specifically low/mid volatility regimes -- the
high-vol tercile had a 0/24 pass rate across the entire grid, so this
strategy should NOT be trusted (or should be explicitly flattened) during
high realized-vol periods. Crypto is decisively out of scope (1/36 grid
cells passed). QQQ is also a viable candidate (mean grid Sharpe up to 1.08
at pzo_period=20/adx=15) but was not separately re-validated this
iteration; a future loop could confirm QQQ or add an explicit high-vol
regime gate to broaden this strategy's usable range.
