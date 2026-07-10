# kardashev

[![PyPI](https://img.shields.io/pypi/v/kardashev)](https://pypi.org/project/kardashev/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/kardashev?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/kardashev)
[![License](https://img.shields.io/pypi/l/kardashev)](https://github.com/kardashev-lab/kardashev-py/blob/main/LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/kardashev)](https://pypi.org/project/kardashev/)

Open energy data for all US ISOs. Direct access to CAISO, ERCOT, MISO, NYISO, ISONE, SPP, and PJM, no gridstatus dependency. Most endpoints need no API key; ISO-NE and PJM LMP require a free account with that ISO.

## Install

```bash
pip install kardashev
```

## Direct ISO access

```python
from kardashev import CAISO, ERCOT, MISO, NYISO, ISONE, SPP, PJM

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

# PJM (requires PJM_USERNAME + PJM_PASSWORD env vars; free account at dataminer2.pjm.com)
pjm = PJM()
df = pjm.get_lmp(market="RT")       # hourly RT LMP for a pricing node
df = pjm.get_lmp(market="DA")       # hourly DA LMP
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

## Common tasks

Get today's fuel mix for all 7 ISOs in one pass:

```python
from kardashev import Client

kl = Client()
mixes = {iso: kl.fuel_mix(iso=iso) for iso in ["CAISO", "ERCOT", "MISO", "NYISO", "ISONE", "SPP", "PJM"]}
```

Compare real-time LMP across ISOs:

```python
prices = {iso: kl.lmp(iso=iso, market="RT", limit=1) for iso in ["CAISO", "ERCOT", "PJM"]}
```

Latest carbon intensity for every ISO in a single call:

```python
carbon = kl.carbon_latest()
```

Pull an ISO's interconnection queue to a file:

```python
kl.queue(iso="MISO").to_csv("miso_queue.csv")
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
| `curtailment(iso)` | Renewable curtailment |
| `interchange(ba)` | Tie-line power flows for a balancing authority |
| `nat_gas(hub)` | Natural gas spot prices |
| `nat_gas_storage()` | EIA weekly storage report |
| `weather(iso)` | Hourly temperature at representative ISO hub cities |
| `bpa()` | BPA 5-min balancing area: wind, hydro, thermal, load |
| `outages(iso)` | Generator outage reports |
| `outages_summary()` | Total MW in outage by ISO x type |
| `ancillary(iso, market)` | Ancillary service prices |
| `ancillary_latest()` | Latest ancillary snapshot |
| `nuclear_status()` | Nuclear plant capacity factors |
| `nuclear_summary()` | Nuclear fleet capacity/output summary |
| `emissions(iso)` | SO₂/NOₓ emission rates |
| `generation_wind_solar(iso)` | Wind/solar generation forecast |
| `generation_battery()` | Battery storage (CAISO) |
| `generation_btm_solar()` | Behind-the-meter solar (NYISO) |
| `generation_reserve_margins()` | Planning reserve margins |
| `hydro_reservoirs()` | Reservoir storage levels |
| `hydro_reservoirs_latest()` | Latest reservoir snapshot |
| `hydro_streamflow()` | USGS streamflow by site |
| `solar_irradiance()` | Solar irradiance by location |
| `solar_irradiance_locations()` | Tracked irradiance stations |
| `solar_irradiance_latest()` | Latest irradiance snapshot |
| `queue(iso)` | Interconnection queue |
| `commodities_coal()` | Coal prices by rank |
| `commodities_petroleum()` | Petroleum spot prices |
| `commodities_power_burn()` | Gas consumed for power generation |
| `steo_forecast()` | EIA Short-Term Energy Outlook |
| `carbon_markets()` | RGGI/WCI carbon market prices |

Note: `outages()` (unit-level generator outages), `commodities_coal()`, and `commodities_power_burn()` currently return a 500 from the hosted API - known backend issues, not client bugs. See [coverage.yaml](https://github.com/kardashev-lab/kardashev-py/blob/main/coverage.yaml). `outages_summary()` and the other commodities endpoints work.

## ISOs supported

CAISO, ERCOT, ISONE, MISO, NYISO, PJM, SPP

## Custom base URL

```python
kl = Client(base_url="https://data.kardashevlabs.org")
```

## Comparison

| | kardashev | gridstatus |
|---|---|---|
| API key required | No, except ISO-NE and PJM LMP (free ISO account) | No (direct ISO access); hosted `gridstatusio` client requires a key |
| License | MIT | BSD-3-Clause |
| US ISO coverage | 7 (CAISO, ERCOT, MISO, NYISO, ISONE, SPP, PJM) | 7 US ISOs + IESO, AESO (Canada), plus EIA |
| Hosted normalized API | Yes, free, no key (`Client`) | Yes, paid tiers (`gridstatusio`) |
| Direct ISO scrapers | Yes, for all 7 ISOs | Yes, for all covered ISOs |
| Datasets | 25+ | 450+ |
| Maturity | Early (2026) | 3+ years, funded, staffed |

Use `gridstatus` if you need Canadian ISOs, EIA data, or the widest dataset catalog. Use `kardashev` if you want a free hosted API with no key for the 7 major US ISOs, or direct scrapers for the same set (no key needed except ISO-NE and PJM LMP).

## Links

- API docs: [data.kardashevlabs.org/docs](https://data.kardashevlabs.org/docs)
- Source: [github.com/kardashev-lab/kardashev-py](https://github.com/kardashev-lab/kardashev-py)
- Changelog: [CHANGELOG.md](https://github.com/kardashev-lab/kardashev-py/blob/main/CHANGELOG.md)
- Dataset coverage by ISO: [coverage.yaml](https://github.com/kardashev-lab/kardashev-py/blob/main/coverage.yaml)
- Data sources and refresh cadence: [SOURCES.md](https://github.com/kardashev-lab/kardashev-py/blob/main/SOURCES.md)
- Website: [kardashevlabs.org](https://kardashevlabs.org)

## License

MIT - see [LICENSE](https://github.com/kardashev-lab/kardashev-py/blob/main/LICENSE).
