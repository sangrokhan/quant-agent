# Backtest Report: Ehlers Decycler Oscillator Dual-Timeframe Crossover (TASC Sept 2015)

**Strategy file:** `strategies/2026-09-17_decycler_osc_dual_crossover.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/09/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

This repo has one prior Decycler Oscillator entry (2026-09-05-046,
rejected), which used a single-oscillator countertrend-snapback rule
approximated from a paywalled third-party source. This iteration uses
Ehlers' own EXACT disclosed formula AND the article's own trading rule:
compute two DecyclerOscillator readings (fast_hp_period=100/fast_k=1.2 and
slow_hp_period=125/slow_k=1.0, the article's own defaults) and trade their
crossover against each other, not either one crossing a fixed threshold.

## Config (article defaults: fast_hp_period=100, fast_k=1.2, slow_hp_period=125, slow_k=1.0)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | PASS (1.077) | FAIL (0.873) |
| Max Drawdown (<=0.25) | PASS (0.194) | PASS (0.166) |
| TC survival (net Sharpe>=0.5) | PASS (1.040) | PASS (0.815) |
| Walk-forward (>=75%) | PASS (4/4) | not run (Sharpe already fails) |
| Parameter sensitivity (<=0.5) | PASS (0.215) | not run |
| Trades | 33 | 38 |

Crypto (BTC/USDT, ETH/USDT, using QQQ's config): decisive reject -- Sharpe
fails both (0.237, 0.239), MDD fails both (0.493, 0.528), TC-survival fails
both (0.102, 0.131).

A broad SPY-specific retune (fast_hp_period in {30-100}, slow_hp_period in
{80-200}, fast_k in {0.8-1.5}) found NO configuration clearing Sharpe>=1.0
while keeping MDD<=0.25 -- SPY's rejection is a genuine Sharpe-ceiling
issue at this crossover construction, not a tuning gap.

## Step 6 grid summary (fast_hp_period in {60,100} x slow_hp_period in {100,150}, 3 vol terciles, equity+crypto, 48 cells)

- `pass_fraction`: 11/48 = 0.229
- `by_asset_class`: equity 10/24, crypto 1/24
- `by_vol_regime`: low 5/16, mid 3/16, high 3/16 (no strong concentration)
- `best_cell`: fast_hp_period=100/slow_hp_period=100 (degenerate, near-equal
  periods), QQQ, low-vol, Sharpe 2.12
- `worst_cell`: fast_hp_period=60/slow_hp_period=150, QQQ, low-vol, Sharpe -0.59

## Decision

**Accept for QQQ only** (article's own default parameters, all 5
validators pass). **Reject for SPY** (Sharpe ceiling ~0.87 confirmed via
broad retune search). **Reject for crypto** decisively.

Scope: narrow accept, QQQ-only, ~33 trades/7.5yr, using the source
article's OWN disclosed parameters unmodified -- a clean confirmation that
Ehlers' exact formula (as opposed to the prior entry's third-party
approximation) produces a genuinely different, partially-passing result.
