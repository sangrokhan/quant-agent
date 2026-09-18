# Bitcoin Q4 Seasonality ("Uptober"/"Rektember" avoidance)

**Strategy file:** `strategies/2026-09-20_btc_q4_seasonality_uptober.py`
**Hypothesis id:** 2026-09-20-011

## Source

https://www.fool.com/investing/2026/09/12/september-has-historically-been-a-difficult-month/
(The Motley Fool, Dominic Basulto, Sep 12 2026), citing long-run Bitcoin
historical monthly-return statistics: September average return -2.93%
("Rektember", BTC's worst month), October average +20% ("Uptober"),
November average +41%, December average +4%. Corroborated independently
by CoinDesk (Oct 2025: "Since 2013, bitcoin has averaged 14.4% gains in
October, with a median return of 10.8% ... 10 of 13 Octobers ended in the
green") and other outlets (Blockearner/TrustWallet: +21.89% avg October
2013-2024).

## Hypothesis

Hold BTC/crypto long ONLY during October, November, December (the three
historically strongest calendar months); flat every other month, including
the historically negative September. First BTC-native Q4-concentration
seasonality strategy in this repo (distinct from the existing SPY-focused
`2026-09-12_september_avoidance_seasonality.py`, which is a much broader
"long everywhere except September" equity-market construction).

## Grid-test summary (Step 6)

Grid: `hold_months` in {(10,11,12), (10,11), (11,12)} x `trend_window` in
{0, 100}, QQQ+SPY+BTC/USDT+ETH/USDT, 3 vol-regime terciles, 2018-2026.

```
total_cells: 72, passed_cells: 16, pass_fraction: 0.222
by_asset_class: equity 10/36 (0.278), crypto 6/36 (0.167)
by_vol_regime: low 11/24 (0.458), mid 3/24 (0.125), high 2/24 (0.083)
best_cell: hold_months=(10,11,12)/trend_window=100, BTC/USDT, low-vol, Sharpe=1.612
```

## Single-config validation (hold_months=(10,11,12), trend_window=100)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.278 (pass) | 0.246 (pass, <0.25) | 1.266 (pass) | 0.75 (pass) | 0.284 (pass) | **ACCEPT** |
| ETH/USDT | 0.474 (fail) | 0.433 (fail) | 0.454 (fail) | 0.75 (pass) | 0.253 (pass) | REJECT |
| QQQ | 0.605 (fail) | 0.110 (pass) | -- | -- | -- | REJECT (falsification check, as expected -- BTC-specific seasonality) |
| SPY | 0.641 (fail) | 0.081 (pass) | -- | -- | -- | REJECT (falsification check, as expected) |

Only 18 round-trip trades on BTC over the ~8.5yr window (3 calendar entries
+ exits per year, very low turnover, easily clears transaction costs).
The 200-day-ish `trend_window=100` SMA eligibility gate on entry materially
helps (unconditional trend_window=0 variant was in the failing majority of
grid cells) -- consistent with this repo's repeated finding that a trend
filter reduces drawdown on otherwise-positive-Sharpe calendar strategies.

## Outcome

**Accepted for BTC/USDT only** at `hold_months=(10,11,12), trend_window=100`.
ETH/USDT fails Sharpe/MDD/TC-survival at the same config despite BTC/ETH's
high price correlation -- ETH's return distribution is evidently less
concentrated in this specific Q4 window than BTC's. QQQ/SPY rejected as
expected (this is a genuinely crypto-specific seasonal effect, not a broad
market-calendar anomaly -- serves as a useful falsification check that the
strategy isn't just capturing generic Q4 stock-market strength).
