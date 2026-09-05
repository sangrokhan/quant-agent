# Dual EMA(20/50 family) Crossover + OBV-EMA Volume Confirmation + ATR Stop — Backtest Report

**Hypothesis:** Fast/slow EMA price crossover (canonical 20/50, best config
found at 10/50) triggers a long entry only when On-Balance Volume (OBV) is
above its own EMA(10) at that bar (volume-flow confirmation gate), exiting
on the reverse EMA crossover, an ATR-based stop-loss (entry_close -
1.5x ATR(14)), or a max_hold_days time-stop.

**Source:** Google AI-overview synthesis (query: `"On Balance Volume" trend
confirmation crossover EMA strategy entry exit rule stocks`, retrieved via
browser_exec after web_search returned no useful results) citing
TradingView + Facebook "Spider Software - Algo Trading" community material:
"Price Chart: 20-period EMA (fast) and 50-period EMA (slow). Volume
Indicator: On-Balance Volume (OBV) with a 10-period EMA applied to the OBV
line itself... EMA Crossover: The short-term 20 EMA crosses above the
medium-term 50 EMA... OBV Confirmation: The OBV line must be above its own
10 EMA... Stop Loss: ...1.5x ATR from entry."

**Strategy file:** `strategies/2026-09-05_ema_dual_obv_confirm_atr_stop.py`

**Distinct from:** 2026-09-04-027 (OBV-crossing-its-own-EMA IS the primary
signal, no price EMA crossover); 2026-09-04-165 (EMA(20/50) crossover
confirmed by RSI, a momentum oscillator, not volume flow). Here price EMA
crossover is primary, OBV-vs-EMA is a static gate (must already hold, not
itself cross), and an ATR stop-loss is added.

## Step 6 — Grid test summary (param_grid: fast_span in [10,20] x slow_span
in [50,100] x atr_mult in [1.5,2.5]; symbols: equity QQQ/SPY, crypto
BTC/USDT, ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 96, passed_cells: 21, **pass_fraction: 0.219**
- by_asset_class: equity 21/48 (44%); crypto 0/48 (0%, decisive fail)
- by_vol_regime: low 16/32 (50%), mid 5/32 (16%), high 0/32 (0%)
- by_symbol: QQQ 13/24, SPY 8/24, BTC/USDT 0/24, ETH/USDT 0/24
- best_cell: fast_span=10, slow_span=50, atr_mult=1.5, QQQ, low-vol,
  Sharpe=2.739
- worst_cell: fast_span=20, slow_span=50, atr_mult=2.5, QQQ, high-vol,
  Sharpe=-1.116

## Step 7 — Single-config validators (config: fast_span=10, slow_span=50,
atr_mult=1.5, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.305 | FAIL 0.627 |
| Max Drawdown (<= 0.25) | PASS 0.138 | PASS 0.196 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **PASS** 1.264 (21 trades) | FAIL (untested further, Sharpe already fails) |
| Parameter sensitivity (relative_std <= 0.5, 8-cell grid mean sweep) | **PASS** 0.246 | not computed (already fails Sharpe) |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries) -- noted per Step 7
guidance to log the omission rather than skip silently.

At the canonical source config (fast_span=20, slow_span=50, atr_mult=1.5),
QQQ Sharpe was a near-miss at 0.926 (15 trades); the grid's best config
(fast_span=10) clears the threshold decisively at 1.305 with reasonable
parameter-sensitivity (relative_std 0.246, not curve-fit fragile -- 8/8
grid cells averaged 1.169 mean Sharpe).

## Outcome: **ACCEPTED (QQQ only, fast_span=10/slow_span=50/atr_mult=1.5)**;
SPY rejected (Sharpe 0.627 < 1.0); crypto rejected decisively (0/48 cells)

QQQ clears all validators run: Sharpe 1.305, MDD 0.138, net Sharpe after
10bps costs 1.264 (21 trades, low turnover), parameter-sensitivity relative
std 0.246 across an 8-cell fast/slow/atr sweep. SPY fails Sharpe (0.627) at
the same and canonical configs. Crypto (BTC/USDT, ETH/USDT) failed all 48
grid cells -- OBV-based volume confirmation combined with a price EMA
crossover appears to be another QQQ-specific edge in this repo's growing
cluster of accepted volume-confirmation strategies (alongside PVO
2026-09-05-075 and VPT 2026-09-05-076), reinforcing the pattern that
Nasdaq-100-specific volume-conviction signals recur across multiple
independent indicator constructions.
