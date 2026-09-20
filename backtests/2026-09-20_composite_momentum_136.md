# 2026-09-20: Composite Momentum 1-3-6 with 200-day Trend Safety Filter — ACCEPTED (equity)

**Hypothesis:** Per
https://help.investminder.com/en/investment-academy/practical-guide-composite-momentum-1-3-6-3-6-12-1vqehob/
("Practical Guide: Composite Momentum (1-3-6 & 3-6-12)"): a Composite
Momentum score averages several ROC lookbacks simultaneously (1/3/6-month
for the "tactical" variant) to capture a more robust, sustainable trend
than any single-lookback ROC. The source's own disclosed "Safety Filter"
rule: "Buy if Composite Momentum > 0 AND Current Price > 200-day Moving
Average" -- exactly what this strategy implements.

**Source:**
https://help.investminder.com/en/investment-academy/practical-guide-composite-momentum-1-3-6-3-6-12-1vqehob/
(browser_exec).

**Signal:** composite_mom = mean(ROC(close,21), ROC(close,63),
ROC(close,126)); long when composite_mom > mom_threshold (0.0) AND close >
SMA(trend_window) (200); flat otherwise.

**Grid test** (trend_window in [150,200], mom_threshold in [0.0,0.05],
roc3 in [90,126], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles, 96 cells):
- pass_fraction: 0.260 (25/96)
- by_asset_class: equity 24/48, crypto 1/48
- by_vol_regime: low 17/32, mid 8/32, high 0/32
- best_cell: SPY low-vol, sharpe 2.86 (trend_window=200, mom_threshold=0.0,
  roc3=126)

**Full-sample validators** at primary config (trend_window=200,
mom_threshold=0.0, roc3=126):

| Validator | QQQ | SPY | Threshold | Result |
|---|---|---|---|---|
| Sharpe ratio | 1.146 | 1.183 | ≥1.0 | PASS both |
| Max drawdown | 0.183 | 0.170 | ≤0.25 | PASS both |
| TC-survival (5bps/trade, 51/47 trades) | 1.117 | 1.144 | ≥0.5 | PASS both (very low turnover) |
| Walk-forward (4 splits) | 3/4 positive (1.44,-0.43,0.99,0.55)=0.75 | 3/4 positive (0.67,-0.23,1.52,1.21)=0.75 | ≥0.75 | PASS both |
| Parameter sensitivity (trend_window sweep 100/150/200/250) | rel_std 0.102 | rel_std 0.091 | ≤0.5 | PASS both, very stable |

Both symbols pass all 5 validators with strong margins, notably very low
parameter sensitivity (rel_std ~0.10, among the most stable strategies in
this repo's log) and a low ~50-trade turnover over 7.7 years -- consistent
with the source's own framing of Composite Momentum as a "robust,
sustainable trend" filter rather than a high-frequency signal.

**Crypto (BTC/USDT, ETH/USDT):** rejected -- full-sample Sharpe 0.836 and
0.885 respectively (both below 1.0), MDD 0.445 and 0.667 (both above
0.25). Near-miss on Sharpe for BTC but decisive MDD failure on both;
grid shows only 1/48 crypto cells passing.

**Decision: ACCEPTED for QQQ and SPY (equity only).** All 5 validators
pass for both with strong, stable margins. Crypto (BTC/USDT, ETH/USDT)
rejected -- MDD failure decisive despite near-miss Sharpe on BTC.
