# Backtest Report: SPY/QQQ Trailing-Momentum Rotation (rejected — MDD)

**Strategy file:** `strategies/2026-09-18_spy_qqq_momentum_rotation.py`
**Knowledge base id:** 2026-09-18-024

## Hypothesis

Per https://github.com/ManusMcMeen/spy-qqq-rotation-strategy's disclosed
README (visited this iteration via `browser_exec` after `web_extract`
errored with "DuckDuckGo (ddgs) is a search-only backend and cannot extract
URL content"): rotate 100% between SPY and QQQ monthly based on trailing
63-trading-day (~3 month) total return -- hold whichever ETF had the higher
lookback return. Source's own reported result (2023-01-01 to 2025-08-07,
~2.6yr sample): CAGR 17.39%, Sharpe 1.29. Tested here independently over
this repo's full available SPY/QQQ history (2010-2026) since the source's
sample is short and unrepresentative of a full market cycle.

Genuinely novel construction for this repo: always fully invested in ONE of
two assets (never flat), rotating capital directly -- distinct from every
existing single-asset trend/momentum strategy and from this repo's existing
single-leg pairs-trade approximations (GLD/SLV, JPM/BAC, GDX/RING, ETH/BTC),
which all gate ONE asset's long/flat exposure via a ratio signal rather than
rotating capital between two always-long legs.

## Parameter search (SPY vs QQQ, lookback_days x rebalance_freq_days,
32-cell full-sample scan, 2010-2026)

Best Sharpe found: 1.075 (lookback_days=42, rebalance_freq_days=5) -- but
**MDD 0.302, failing the 0.25 threshold**. Every single one of the 32
configs tested had MDD > 0.25 (range ~0.286-0.313) -- there is no
lookback/rebalance-frequency combination that keeps this strategy's
full-100%-concentrated, always-fully-invested-in-one-asset construction
under the repo's max-drawdown bar. This is an inherent structural property
of the strategy (never holding cash/flat, 100% notional in either SPY or
QQQ at all times) rather than a parameter-tuning failure -- both legs
experienced >30% peak-to-trough equity-curve drawdowns during the sample
(e.g. 2020 COVID crash, 2022 rate-hike bear market) regardless of which leg
was held at the time.

Crypto (BTC/USDT vs ETH/USDT) rotation was also tested for completeness:
best Sharpe 0.975 (lookback_days=21, rebalance_freq_days=5) but MDD 0.798 --
even more decisively rejected (crypto's baseline volatility makes an
always-100%-invested single-asset rotation construction structurally
incompatible with any reasonable drawdown bar).

## Decision

**Rejected across all asset pairs (SPY/QQQ and BTC/ETH).** Best Sharpe
(1.075, SPY/QQQ, lb=42/rb=5) clears the 1.0 Sharpe threshold but fails Max
Drawdown decisively (0.302 vs 0.25 threshold) -- and no parameter
combination in the 32-cell scan found an MDD < 0.25 config, so this is not
a near-miss worth a follow-up parameter retune. A future revisit of this
idea would need an architectural change (e.g. an allocation blend/leverage
cap rather than 100%-concentrated rotation, or a cash/bond fallback leg when
BOTH assets show negative trailing momentum) rather than further tuning
within the existing two-asset-always-fully-invested parameter space.
