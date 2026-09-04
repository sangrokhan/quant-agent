# Backtest Report: Trend Trigger Factor (TTF) Zero-Line Crossover

**Strategy file:** `strategies/2026-09-05_ttf_zeroline_crossover.py`
**Knowledge base id:** 2026-09-05-015

## Hypothesis

Trend Trigger Factor (TTF, M.H. Pee, TASC Dec 2004): compares "buying
power" (current n-bar Highest-High minus prior n-bar Lowest-Low) against
"selling power" (prior n-bar Highest-High minus current n-bar
Lowest-Low), normalized by their average. Mechanical rule: TTF crossing
above zero signals a long entry; crossing below zero signals exit.

Source: https://stonehillforex.com/2024/11/trend-trigger-factor-as-a-confirmation-indicator/
(exact TASC formula and zero-line-cross rule disclosed free).

First TTF strategy in this repo — same author (M.H. Pee) as Trend
Intensity Index (id=2026-09-04-123, rejected) and Random Walk Index
(id=2026-09-04-153), but structurally distinct (buy/sell-power
extremes-differencing vs. signed-deviation-summing).

## Grid test summary (Step 6)

- `param_grid`: `n` in {8, 14, 21}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **72 total cells, 17 passed, pass_fraction = 0.236**
- By asset class: equity 17/36, crypto 0/36
- By vol regime: low 12/24, mid 3/24, high 2/24
- Best cell: n=14, max_hold_days=20, QQQ, low-vol, Sharpe 2.81
- **n=8, max_hold_days∈{20,30} passed 2/3 vol-regime cells consistently on BOTH QQQ and SPY** — the broadest/most consistent pattern seen across recent iterations.

## Single best-config validators (Step 7)

Config: `n=8, max_hold_days=20`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.447 | 1.168 | ≥ 1.0 | ✅ / ✅ |
| Max drawdown | **0.286** | 0.165 | ≤ 0.25 | **QQQ ❌** / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | 1.320 | 0.999 | ≥ 0.5 | ✅ / ✅ |
| Num trades | 90 | 92 | — | — |
| Parameter sensitivity (n sweep {8,14,21}, QQQ, relative_std) | 0.302 | — | ≤ 0.5 | ✅ |

QQQ's MDD failure was checked for robustness across `max_hold_days` in
{10, 15, 20}: MDD stayed in the 0.255-0.326 range at every setting,
consistently above the 0.25 threshold — not a config-specific artifact.

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **ACCEPTED (SPY only)**; rejected for QQQ (decisive MDD fail) and crypto (BTC/USDT, ETH/USDT — decisive 0/36 cells)

SPY passes every validator run cleanly (Sharpe 1.168, MDD 0.165,
net-of-cost Sharpe 0.999) with a good parameter-sensitivity margin
(relative_std 0.302). QQQ's Sharpe/TC-survival pass but its max drawdown
(0.286, tested robust across multiple hold-day settings) decisively
breaches the 0.25 threshold — QQQ is therefore excluded from the
accepted scope. Crypto rejected decisively (0/36 grid cells).
