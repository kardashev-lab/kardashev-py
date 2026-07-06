# kardashev

[![PyPI](https://img.shields.io/pypi/v/kardashev)](https://pypi.org/project/kardashev/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/kardashev?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/kardashev)
[![License](https://img.shields.io/pypi/l/kardashev)](https://github.com/kardashev-lab/kardashev-py/blob/main/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/kardashev)](https://pypi.org/project/kardashev/)

Open energy data for all US ISOs. Direct access to CAISO, ERCOT, MISO, NYISO, ISONE, SPP, and PJM - no API key, no rate limits, no gridstatus dependency.

## Install

```bash
pip install kardashev
```

## Direct ISO access (no API key)

```python
from kardashev import CAISO, ERCOT, MISO, NYISO, ISONE, SPP

# CAISO
caiso = CAISO()
df = caiso.get_fuel_mix()           # live generation by fuel type
df = caiso.get_load()               # actual grid load
df = caiso.get_lmp(market="RT")     # real-time LMP (TH_NP15 hub)
df = caiso.get_lmp(market="DA", node="TH_SP15_GEN-APND")
df = caiso.get_curtailment()        # solar + wind curtailment

# ERCOT
ercot = ERCOT()
df = ercot.get_fuel_mix()
rows = ercot.get_lmp(market="RT")   # settlement point prices (CDR)
rows = ercot.get_lmp(market="DA")   # DAM hourly prices

# MISO
miso = MISO()
df = miso.get_fuel_mix()
rows = miso.get_lmp(market="RT")    # 5-min hub prices
rows = miso.get_lmp(market="DA")    # ex-ante DA LMP

# NYISO
nyiso = NYISO()
df = nyiso.get_fuel_mix()
df = nyiso.get_lmp(market="RT")     # real-time zonal LMP
df = nyiso.get_lmp(market="DA")     # day-ahead zonal LMP

# ISONE (LMP requires ISONE_USERNAME + ISONE_PASSWORD env vars)
isone = ISONE()
df = isone.get_fuel_mix()
df = isone.get_lmp(market="RT", location=".Z.NEPOOL")

# SPP
spp = SPP()
df = spp.get_fuel_mix()
df = spp.get_lmp()                  # latest RTBM prices
```

## Managed API (optional)

Use `Client` to query the [Kardashev Labs API](https://data.kardashevlabs.org) - adds carbon intensity, LMP history, interconnection queues, and 25+ more endpoints with a single hosted backend.

```python
from kardashev import Client

kl = Client()

# Live fuel mix for CAISO
fuel = kl.fuel_mix(iso="CAISO")

# Real-time LMP hub prices for MISO
prices = kl.lmp(iso="MISO", market="RT", limit=50)

# Carbon intensity (lbs CO₂/MWh) for ERCOT
carbon = kl.carbon(iso="ERCOT")

# All nodes with latest LMP for the map view
nodes = kl.lmp_map(iso="PJM", market="RT")
```

## Endpoints

| Method | Description |
|---|---|
| `fuel_mix(iso)` | Generation by fuel type |
| `carbon(iso)` | Carbon intensity (lbs CO₂/MWh) |
| `carbon_latest()` | Latest carbon intensity for all ISOs |
| `lmp(iso, market, node_id, limit)` | LMP price history |
| `lmp_map(iso, market)` | All nodes with latest price + coordinates |
| `lmp_hubs(iso)` | Hub/zone node list |
| `load(iso)` | Actual grid load |
| `load_forecast(iso)` | Load forecast |
| `generation(iso)` | Generation by unit type |
| `curtailment(iso)` | Renewable curtailment |
| `interchange(iso)` | Tie-line power flows |
| `nat_gas(hub)` | Natural gas spot prices |
| `nat_gas_storage()` | EIA weekly storage report |
| `weather(city)` | Weather observations |
| `outages(iso)` | Generator outage reports |
| `ancillary(iso, market)` | Ancillary service prices |
| `nuclear_status()` | Nuclear plant capacity factors |
| `emissions(iso)` | SO₂/NOₓ emission rates |
| `hydro(iso)` | Hydro generation |
| `solar(iso)` | Solar generation |
| `queue(iso)` | Interconnection queue |
| `commodities()` | Power/gas commodity prices |
| `carbon_markets()` | RGGI/WCI carbon market prices |

## ISOs supported

CAISO, ERCOT, ISONE, MISO, NYISO, PJM, SPP

## Custom base URL

```python
kl = Client(base_url="https://data.kardashevlabs.org")
```

## Links

- API docs: [data.kardashevlabs.org/docs](https://data.kardashevlabs.org/docs)
- Source: [github.com/kardashev-lab/kardashev-py](https://github.com/kardashev-lab/kardashev-py)
- Changelog: [CHANGELOG.md](https://github.com/kardashev-lab/kardashev-py/blob/main/CHANGELOG.md)
- Website: [kardashevlabs.org](https://kardashevlabs.org)

## License

MIT - see [LICENSE](https://github.com/kardashev-lab/kardashev-py/blob/main/LICENSE).
