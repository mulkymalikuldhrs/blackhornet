#!/usr/bin/env python3
"""
Performance profiling for BlackHornet.

Profiles:
- deploy_nest (sync)
- async_deploy_nest (async)
- start_hornets (service startup)

Writes JSON summary to data/performance-profile.json
"""

import json, time, asyncio
from pathlib import Path
from blackhornet import BlackHornetNest

out_path = Path(__file__).parent / "data" / "performance-profile.json"
out_path.parent.mkdir(parents=True, exist_ok=True)

def time_func(fn, *a, **kw):
    start = time.time()
    fn(*a, **kw)
    return round(time.time() - start, 3)

nest = BlackHornetNest()
data = {}
data["deploy_nest"] = {"calls": 1, "total_time_s": time_func(nest.deploy_nest)}

async def async_part():
    async_nest = BlackHornetNest()
    return time_func(async_nest.async_deploy_nest)

data["async_deploy_nest"] = {"calls": 1, "total_time_s": asyncio.run(async_part())}

data["start_hornets"] = {"calls": 1, "total_time_s": time_func(nest.start_hornets)}

with out_path.open("w") as f:
    json.dump(data, f, indent=2)
print(f"Profile written to {out_path}")