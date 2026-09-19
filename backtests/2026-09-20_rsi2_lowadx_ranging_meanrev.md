# RSI(2-3) Mean Reversion Gated by Low ADX (Ranging-Market Filter)

**Strategy file:** `strategies/2026-09-20_rsi2_lowadx_ranging_meanrev.py`
**Source:** https://www.quantifiedstrategies.com/rsi-adx-trading-strategy/ (read in-browser; "Trading Rules" boxes are members-only, but the article's Key Takeaways and body text give explicit testable parameter guidance: RSI/IBS best with short 2-3 day lookbacks for mean-reversion; ADX best with a short 5-10 day period and 30-40 threshold rather than the popular 14/25).

## Hypothesis
Use a short-period RSI(2-3) oversold entry, gated by ADX(5-10) **below** a
threshold (ranging-market confirmation, opposite polarity from this repo's
prior ADX-above-threshold trend filters), since the source explicitly frames
RSI/IBS as mean-reversion tools and ADX as best for identifying whether a
trend-following or mean-reversion regime currently applies.

## Grid test summary (QQQ/SPY/BTC-USDT/ETH-USDT, 2019-2026, vol_regime_splits=3)
- param_grid: rsi_period=[2,3,5] x adx_max=[25,30,40] x rsi_oversold=[10,15]
- total cells: 216, passed: 20 (pass_fraction 9.3%)
- by_asset_class: equity 19/108 (17.6%), crypto 1/108 (0.9%) — crypto decisively rejected
- by_vol_regime: low 12/72, mid 0/72, high 8/72 — mid-vol regime is a total wipeout
- best single cell: QQQ, rsi_period=3/adx_max=40/rsi_oversold=15, low-vol, Sharpe 1.71
- best *averaged-across-regimes* config: rsi_period=2/adx_max=40/rsi_oversold=10 (QQQ avg 0.994, SPY avg 1.006)

## Single-config validators (rsi_period=2, adx_max=40.0, rsi_oversold=10.0, rsi_exit=60.0, max_hold_days=10)

| Validator | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe ratio | 0.873 | 0.941 | >= 1.0 | **FAIL both** |
| Max drawdown | 0.105 | 0.100 | <= 0.25 | pass both |
| Tx-cost survival (10bps/trade) | net Sharpe 0.739 (68 trades) | net Sharpe 0.757 (76 trades) | >= 0.5 | pass both |
| Walk-forward (manual 4-split; `check_walk_forward` hits the known vectorbt `RangeSplitter` AttributeError bug) | 1.0 (4/4) | 0.75 (3/4) | >= 0.75 | pass both |
| Parameter sensitivity (grid-derived relative_std across the 14-15 cell param sweep) | 0.709 | 1.581 | <= 0.5 | **FAIL both** |

## Decision: REJECTED (both QQQ and SPY fail full-sample Sharpe AND parameter sensitivity; crypto decisively rejected on the grid)

Full-sample Sharpe (0.87-0.94) falls just short of the 1.0 threshold despite
strong isolated grid cells (up to 1.71 in low-vol regimes) — the mid-vol
regime wipeout (0/72 grid cells) drags the full-sample average down.
Parameter sensitivity fails badly (relative_std 0.71-1.58, more than triple
the threshold in SPY's case) because performance varies wildly across the
adx_max/rsi_period/rsi_oversold grid (e.g. rsi_period=5 configs go strongly
negative on SPY). This confirms the source's own framing only works as a
regime *classifier*, not as a standalone tradeable edge at any single fixed
parameterization — a future loop could revisit with the ADX gate applied to
a stronger base mean-reversion signal (e.g. IBS, which this article also
recommends and this repo has already validated standalone) rather than to
bare RSI(2-3).
