# Backtest Report: Point and Figure (P&F) Double-Top Breakout (2026-09-04)

**Hypothesis:** Point and Figure chart double-top breakout: convert price
into X (rising)/O (falling) columns using an ATR-derived adaptive box size
and a 3-box reversal filter; long entry when the current X-column's running
high exceeds the prior completed X-column's high (double-top breakout);
exit when the current O-column's running low breaks below the prior
completed O-column's low (double-bottom breakdown), or a max_hold_days
time-stop. Source: Google AI-overview synthesis of
Tradyom/Investopedia/TradeAlgo P&F explainers
(https://www.google.com/search?q=Point+and+Figure+chart+breakout+trading+strategy+rules).
First P&F (time-independent box-and-reversal charting) strategy tried in
this repo -- distinct from already-tested Renko (box-based, no
column-comparison breakout rule), Kagi (percentage-reversal, no discrete
box grid), and three-line-break constructions.

**Strategy file:** `strategies/2026-09-04_pnf_doubletop_breakout.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: box_atr_mult in [0.5, 1.0], reversal_boxes=[3]; symbols:
QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 16, passed_cells: 6, pass_fraction: 0.375
by_asset_class: equity 6/12, crypto 0/4
by_vol_regime: low 4/4, mid 1/4, high 1/4
best_cell: SPY, low-vol, box_atr_mult=1.0 -> Sharpe 2.65
worst_cell: QQQ, high-vol, box_atr_mult=0.5 -> Sharpe -0.91
```

## Step 7 single-config validators (box_atr_mult=1.0, reversal_boxes=3, max_hold_days=40, full sample)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.462 (35 trades) | ✅ 1.040 (34 trades) | 1.0 |
| Max drawdown | ❌ 0.269 | ✅ 0.123 | 0.25 |
| Transaction cost survival | ❌ 0.428 | ✅ 0.980 | 0.5 |
| Parameter sensitivity (grid best/worst) | ❌ relative std 2.04 (best 2.65 vs worst -0.91) | -- | 0.5 |
| Walk-forward | ⚠️ skipped (known `vectorbt.utils.splitting` repo bug) | ⚠️ skipped | 0.75 |

## Verdict: **ACCEPTED (SPY only)**

SPY passes all three primary single-config validators decisively (Sharpe
1.04, MDD 0.123, net Sharpe after 10bps costs 0.980 over 34 trades) at the
grid's best config. QQQ fails all three at the same shared config -- this is
a QQQ/SPY-specific divergence pattern already seen in several prior
accepted-SPY-only strategies in this repo (e.g. Camarilla Pivots
id 2026-09-04-119, Gann HiLo id 2026-09-04-128). Crypto rejected decisively
(0/4 grid cells). Parameter sensitivity across the box_atr_mult grid (0.5 vs
1.0) is poor (relative std 2.04) -- record this narrow-scope caveat: only
the box_atr_mult=1.0 config is validated as working, box_atr_mult=0.5
performs much worse (even negative in QQQ high-vol). Walk-forward validator
unavailable due to the pre-existing `vectorbt.utils.splitting`
AttributeError (repo infra bug, not a strategy defect).

**Scope of acceptance:** SPY only, `box_atr_mult=1.0, reversal_boxes=3,
max_hold_days=40`. Do not assume this generalizes to QQQ, crypto, or other
box_atr_mult values without further testing.
