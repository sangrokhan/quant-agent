"""Strategy: SMA(200) trend gate with continuous Ultimate Oscillator sizing
(equity-only accepted variant, deadband=0.5).

QQQ config: sensitivity=0.3, deadband=0.5, leverage_cap=1.0 -- all 5
validators pass. See strategies/2026-09-17_ultimate_oscillator_sizing_sma_trend.py
for the full hypothesis and formula. This module is a thin re-export at
the accepted config for documentation/reproducibility purposes only; the
grid-tested base module is the source of truth.
"""

from __future__ import annotations

import importlib.util
import os

_BASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "2026-09-17_ultimate_oscillator_sizing_sma_trend.py",
)
_spec = importlib.util.spec_from_file_location("uo_sizing_base_mod", _BASE_PATH)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

ACCEPTED_PARAMS = dict(sensitivity=0.3, deadband=0.5, leverage_cap=1.0)


def generate_signals(price_df, **kwargs):
    params = dict(ACCEPTED_PARAMS)
    params.update(kwargs)
    return _base.generate_signals(price_df, **params)


def generate_returns(price_df, **kwargs):
    params = dict(ACCEPTED_PARAMS)
    params.update(kwargs)
    return _base.generate_returns(price_df, **params)
