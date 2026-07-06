# Changelog

## 0.3.0

Bug fix release: six `Client` methods were silently calling endpoints that don't exist on the hosted API (always returned 404). Fixed by pointing them at the real endpoints, which required splitting a few into named sub-methods since the API doesn't expose a single unified endpoint for these datasets.

- Fix `queue()`: was calling `/queue` (404), now calls `/interconnection-queue`
- Fix `nuclear_status()`: was calling `/nuclear/status` (404), now calls `/nuclear`; add `nuclear_summary()` for `/nuclear/summary`
- Fix `nuclear_summary()`/`/nuclear/summary` returning a single object, not rows - no longer routed through the DataFrame converter
- Replace `generation()` (called nonexistent `/generation`) with `generation_wind_solar()`, `generation_battery()`, `generation_btm_solar()`, `generation_reserve_margins()`
- Replace `hydro()` (called nonexistent `/hydro`) with `hydro_reservoirs()`, `hydro_reservoirs_latest()`, `hydro_streamflow()`
- Replace `solar()` (called nonexistent `/solar`) with `solar_irradiance()`, `solar_irradiance_locations()`, `solar_irradiance_latest()`
- Replace `commodities()` (called nonexistent `/commodities`) with `commodities_coal()`, `commodities_petroleum()`, `commodities_power_burn()`, `steo_forecast()`
- Add `outages_summary()` and `ancillary_latest()` to README endpoint table (existed in code, were undocumented)
- Note two known backend issues (not client bugs): `outages()` and `commodities_coal()`/`commodities_power_burn()` currently 500 from the hosted API - see `coverage.yaml`

This is a breaking change for the four replaced methods, but since they always 404'd, no working caller could have depended on their old signatures.

## 0.2.5

- Add `coverage.yaml` (per-ISO dataset support matrix, generated from actual method inventory)
- Add `SOURCES.md` (data sources and refresh cadence for direct ISO access and the hosted API)
- Add "Common tasks" section to README

## 0.2.4

- Add `py.typed` marker
- Add `examples/` directory with runnable scripts for direct ISO access, LMP, carbon intensity, map nodes, and interconnection queue
- Add `CONTRIBUTING.md`
- Add comparison table to README

## 0.2.3

- Add PyPI keywords/classifiers, MIT `LICENSE` file, and this changelog
- Fix `__version__` mismatch (was reporting 0.2.0)

## 0.2.2

- Fix trailing footer/disclaimer rows in NYISO and CAISO interconnection queue parsers

## 0.2.1

- Fix interconnection queue: dead NYISO/ISONE URLs, missing PJM function, add CAISO/ERCOT/MISO/SPP

## 0.2.0

- Add direct ISO classes: `CAISO`, `ERCOT`, `MISO`, `NYISO`, `ISONE`, `SPP`, `PJM` - no API key required, positions this as a `gridstatus` alternative

## 0.1.2

- Copy cleanup

## 0.1.1

- Add README, PyPI description

## 0.1.0

- Initial release: Python client library for the Kardashev Labs data API
