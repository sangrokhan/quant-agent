# Ehlers CyberCycle vs Trigger crossover trend/cycle following

**Strategy file:** `strategies/2026-09-13_ehlers_cybercycle_crossover.py`
**Hypothesis id:** 2026-09-13-032

## Source

Ehlers CyberCycle formula (John F. Ehlers, "Rocket Science for Traders"),
confirmed via Bing SERP featured snippet this iteration:
`web_search` (DDGS backend) failed with a TLS `RequestError` on the first
query attempted; browser_exec Bing fallback used for the whole iteration.

```
alpha = 2 / (Length + 1)
Smooth_t = (Price_t + 2*Price_{t-1} + 2*Price_{t-2} + Price_{t-3}) / 6
Cycle_t = (1 - 0.5*alpha)^2 * (Smooth_t - 2*Smooth_{t-1} + Smooth_{t-2})
          + 2*(1-alpha)*Cycle_{t-1} - (1-alpha)^2*Cycle_{t-2}
Trigger_t = Cycle_{t-1}
```

Long when Cycle crosses above Trigger (gated by close > SMA(trend_window)),
flat on mirror cross or trend-filter break, or a max_hold_days time-stop.

## Grid test (Step 6)

`length` in [8,10,15] x `trend_window` in [50,100,150], equity (QQQ, SPY) +
crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3 -> 108 cells.

- pass_fraction: 0.213 (23/108)
- by_asset_class: equity 23/54, crypto 0/54
- by_vol_regime: low 18/36, mid 2/36, high 3/36
- best_cell: QQQ, length=8/trend_window=50, low-vol, Sharpe=2.511
- worst_cell: SPY, length=8/trend_window=50, mid-vol, Sharpe=-0.760

Crypto rejected decisively (0/54) -- consistent with this repo's other
Ehlers-family cycle/trend strategies not transferring to BTC/ETH.

## Single-config validation (Step 7)

Fine parameter search per symbol (length x trend_window x max_hold_days):

**QQQ** (length=8, trend_window=200, max_hold_days=20):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.031 | >=1.0 | Yes |
| Max drawdown | 0.110 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 178 trades) | 0.669 | >=0.5 | Yes |
| Walk-forward (4 splits) | 0.75 (3/4) | >=0.75 | Yes |
| Parameter sensitivity (rel std, 16-combo local sweep) | 0.081 | <=0.5 | Yes |

All 5 validators pass -> **ACCEPTED for QQQ**.

**SPY** (best found: length=12, trend_window=120, max_hold_days=20):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.075 | >=1.0 | Yes |
| Max drawdown | 0.110 | <=0.25 | Yes |
| TC survival (net Sharpe, 10bps/trade, 173 trades) | 0.499 | >=0.5 | **No** (near-miss, off by 0.001) |
| Walk-forward (4 splits) | 1.0 (4/4) | >=0.75 | Yes |
| Parameter sensitivity | 0.341 | <=0.5 | Yes |

An exhaustive local sweep (length in [8,10,12,15,18,20] x trend_window in
[80,100,120,150,200] x max_hold_days in [15,20,25,30,40], filtered to
Sharpe>=1.0 and MDD<=0.25) found **zero** configs that also clear the
TC-survival threshold for SPY -- every Sharpe/MDD-passing config trades
frequently enough (150-200+ trades over the sample) that transaction costs
push net Sharpe just under 0.5. SPY is logged as a genuine, non-fixable
(within this parameter space) near-miss rather than a candidate for further
per-symbol tuning.

## Outcome

**Accepted for QQQ only** (length=8, trend_window=200, max_hold_days=20).
SPY rejected (TC-survival near-miss). Crypto (BTC/USDT, ETH/USDT) rejected
decisively per the grid test.
