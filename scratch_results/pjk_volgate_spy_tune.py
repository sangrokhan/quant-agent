import importlib.util
import sys
import json
from datetime import datetime
import itertools

sys.path.insert(0, "data")
sys.path.insert(0, "validation")

spec = importlib.util.spec_from_file_location(
    "strat_mod", "strategies/2026-09-18_pjk_channel_trade_in_bands_volgate.py"
)
strat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strat)

import vectorbt as vbt  # noqa: F401,E402
from loaders import load_equity  # noqa: E402

start = datetime(2016, 1, 1)
end = datetime(2026, 9, 1)
price_df = load_equity("SPY", start, end)

results = []
for period, zone, vr in itertools.product([40, 50, 60], [0.2, 0.3, 0.4], [1.1, 1.3, 1.6]):
    r = strat.generate_returns(price_df, period=period, zone=zone, vol_regime_ratio=vr)
    sh = r.vbt.returns(freq="D").sharpe_ratio() if len(r) else None
    mdd = abs(r.vbt.returns(freq="D").max_drawdown())
    results.append((period, zone, vr, sh, mdd))

results.sort(key=lambda x: -(x[3] or -99))
for row in results[:10]:
    print(row)
