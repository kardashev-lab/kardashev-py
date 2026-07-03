# kardashev

Python client for the [Kardashev Labs](https://kardashevlabs.org) energy data API - a free, open energy data platform covering LMP prices, grid load, fuel mix, carbon intensity, curtailment, interconnection queues, and more across all major US ISOs.

## Install

```bash
pip install kardashev
```

## Quick start

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
- Website: [kardashevlabs.org](https://kardashevlabs.org)
