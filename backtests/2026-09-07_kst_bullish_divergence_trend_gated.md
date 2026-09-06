# KST Bullish Divergence + Signal-Line Cross + 200 EMA Trend Filter

**Hypothesis:** Per https://theindicatorlab.com/reviews/kst-know-sure-thing/,
source's own disclosed "highest probability setup": (1) trend filter --
price above 200 EMA for longs, (2) bullish divergence -- price lower low
while KST makes a higher low, (3) KST crosses above its signal line -> long
entry. Exit on KST crossing back below signal line, or KST hitting an
extreme reading (>100 on daily, tested variant also at 80). Source claims a
70% win rate on SPY with this combo since May.

Source: https://theindicatorlab.com/reviews/kst-know-sure-thing/. Distinct
from both existing KST strategies in this repo (2026-09-04-057, plain
signal-line cross at/below zero; 2026-09-06-100, TrendSpider zero-line
cross) -- neither uses divergence detection or a 200 EMA trend gate.

## Step 6 — Grid test (divergence_lookback in {10,20,30}, extreme_exit in
{80,100}, equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT} daily bars,
vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 72, passed: 8, **pass_fraction = 0.111**
- By asset class: equity 4/36, crypto 4/36 (both weak, roughly even for once)
- By vol regime: low 0/24, mid 6/24, high 2/24
- Best cell: QQQ, divergence_lookback=10, extreme_exit=80, high-vol regime,
  Sharpe 1.267
- Worst cell: QQQ, divergence_lookback=20, extreme_exit=80, low-vol regime,
  Sharpe -0.869

## Step 7 — Single-config validators (divergence_lookback=10, extreme_exit=80,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.666 | FAIL 0.768 | FAIL (decisive) 0.236 | FAIL 0.589 |
| Max Drawdown (<= 0.25) | PASS 0.063 | PASS 0.028 | PASS 0.126 | PASS 0.056 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.616 (8 trades) | PASS 0.715 (6 trades) | FAIL 0.215 (8 trades) | PASS 0.579 (6 trades) |
| Parameter sensitivity (relative_std <= 0.5, divergence_lookback {10,20,30} sweep, QQQ) | **FAIL 0.919** | | | |

Walk-forward not run: pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version.

## Outcome: **REJECTED**

Full-sample Sharpe fails on all four symbols (best is SPY's 0.768, still a
clear miss of the 1.0 bar), and QQQ's parameter sensitivity is decisively
unstable (relative_std 0.919, more than double the 0.5 threshold) — the
divergence_lookback sweep produces wildly different Sharpes (10 vs 20 vs 30
bars), suggesting the divergence-detection logic is fragile/overfit to the
specific lookback rather than capturing a robust pattern. Trade counts are
also very low (6-8 trades over 7.5 years per symbol) due to the compound
divergence+trend+crossover gating, making the full-sample Sharpe estimate
itself statistically thin. The source's claimed 70% SPY win rate did not
translate into an acceptable risk-adjusted return once implemented and
tested mechanically across the full sample.
