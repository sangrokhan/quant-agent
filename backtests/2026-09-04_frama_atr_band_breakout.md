# FRAMA ATR-band breakout — backtest report

**Strategy file:** `strategies/2026-09-04_frama_atr_band_breakout.py`
**Hypothesis id:** 2026-09-04-132

## Hypothesis

John Ehlers' Fractal Adaptive Moving Average (FRAMA): an EMA whose alpha is
recomputed every bar from the fractal dimension D of price (N1/N2
half-window ranges vs N3 full-window range, D=(log(N1+N2)-log(N3))/log(2),
alpha=exp(-4.6*(D-1))). Per
[oxfordstrat.com](https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/)'s
own systematic-strategy specification (Ehlers' original design, tested on
42 futures markets over 36 years): long entry when close breaks above
FRAMA + atr_band*ATR(length); trend-exit when close breaks back below
FRAMA - 0.5*atr_band*ATR(length) (a tighter inner band).

Source: https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/
(via browser_exec Google-search fallback), plus a follow-up Google search
confirming the exact FRAMA fractal-dimension formula (N1/N2/N3, alpha
formula) from alphax.trading/MQL5 snippets.

## Grid summary (Step 6)

`length` in {16,20,30} x `atr_band` in {1.0,1.5} x `max_hold_days`
in {10,15}, symbols QQQ/SPY/BTC/USDT/ETH/USDT, vol_regime_splits=3:

- 144 cells total, 33 passed (pass_fraction=0.229)
- by_asset_class: equity 33/72, crypto 0/72
- by_vol_regime: low 19/48, mid 10/48, high 4/48
- best_cell: length=30, atr_band=1.0, max_hold_days=15, QQQ, low-vol, Sharpe=2.18
- worst_cell: length=20, atr_band=1.0, max_hold_days=15, SPY, mid-vol, Sharpe=-0.44

## Primary config validators (length=30, atr_band=1.0, max_hold_days=15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.879 **FAIL (near-miss)** | 0.851 **FAIL (near-miss)** |
| Max drawdown (<=0.25) | 0.186 PASS | 0.140 PASS |
| Net Sharpe after costs (>=0.5, 10bps/trade) | 0.765 PASS (72 trades) | 0.708 PASS (67 trades) |
| Walk-forward (4-split, >=0.75 pass_frac) | 0.75 PASS | 0.75 PASS |
| Parameter sensitivity (rel.std<=0.5, length in {16,20,30}) | 0.019 PASS | 0.150 PASS |

## Decision

**Reject (both QQQ and SPY, near-miss).** Sharpe is a genuine near-miss on
both symbols (0.879/0.851 vs 1.0 threshold) while every other validator
passes cleanly -- MDD comfortably under threshold, TC-survival strong even
at ~70 trades, walk-forward exactly at the 0.75 threshold on both, and
parameter-sensitivity is unusually stable (QQQ rel.std=0.019, essentially
flat across length in {16,20,30}). This is one of the strongest
across-the-board near-misses logged so far -- crypto rejected outright
(0/72 grid cells), but the equity result is a strong candidate for a
future iteration to retest with a slightly tighter atr_band or a small
trend/volume filter to try to clear Sharpe 1.0.
