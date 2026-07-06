# Data sources and refresh cadence

## Direct ISO access (no API key)

The `CAISO`, `ERCOT`, `MISO`, `NYISO`, `ISONE`, `SPP`, and `PJM` classes fetch directly from each grid operator's own public data feed at call time - there is no caching layer, so freshness matches the ISO's own publishing cadence.

| ISO | Source | Auth |
|---|---|---|
| CAISO | [OASIS](https://oasis.caiso.com/oasisapi/) (LMP), [caiso.com/outlook](https://www.caiso.com/outlook/current/fuelsource.csv) (fuel mix, load, curtailment) | None |
| ERCOT | [MIS](https://mis.ercot.com/misdownload/servlets/mirDownload) (fuel mix, LMP, ancillary services) | None |
| MISO | [public-api.misoenergy.org](https://public-api.misoenergy.org/api) (fuel mix, binding constraints, interchange), [docs.misoenergy.org/marketreports](https://docs.misoenergy.org/marketreports) (LMP) | None |
| NYISO | [mis.nyiso.com](https://mis.nyiso.com/public/csv) (fuel mix, load, LMP, queue) | None |
| ISO-NE | [irtt.iso-ne.com](https://irtt.iso-ne.com/reports/external) (fuel mix, load, queue); LMP requires a free ISO-NE web services account | `ISONE_USERNAME` / `ISONE_PASSWORD` for LMP only |
| SPP | [marketplace.spp.org](https://marketplace.spp.org/chart-api/gen-mix/asFile) (fuel mix, curtailment), [portal.spp.org](https://portal.spp.org/file-browser-api/download) (LMP) | None |
| PJM | [DataMiner2](https://dataminer2.pjm.com/feed) (LMP only) | `PJM_USERNAME` / `PJM_PASSWORD`, free account at dataminer2.pjm.com |

See `coverage.yaml` for which datasets each ISO class supports.

## Hosted API (`Client`, data.kardashevlabs.org)

The hosted API ingests from the same direct ISO sources above (via this same `kardashev` package server-side), plus EIA, EPA, and other federal sources, then stores and serves it on a fixed refresh schedule:

| Refresh cadence | Datasets |
|---|---|
| Every 5 minutes | Fuel mix, real-time load, real-time LMP, wind/solar generation, battery storage, BPA, binding constraints, ancillary services |
| Every 15 minutes | ERCOT fuel mix |
| Hourly | Load, day-ahead LMP, load forecasts, reserve margins, temperatures, interchange, EIA fuel mix (all BAs), solar irradiance |
| Daily | Curtailment, natural gas prices, gas storage, NRC reactor status, EPA emissions, USBR reservoirs, interconnection queues (NYISO, PJM, ISO-NE) |
| Weekly | EIA static datasets, carbon allowance (RGGI/WCI) prices |
| Monthly | ERCOT large-load queue |

Carbon intensity (`carbon`, `carbon_latest`) is computed at query time from the latest fuel mix plus EPA eGRID emission factors, so it refreshes on the same cadence as fuel mix (5 minutes).

## Known limitations

- Direct ISO scrapers depend on each ISO's page/file format and are not versioned by the ISO - they can break without notice if an ISO changes its feed.
- ISO-NE and PJM require a free account with the ISO for LMP data; all other datasets on those two ISOs work with no credentials.
- The hosted API's interconnection queue data currently covers NYISO, PJM, and ISO-NE on the daily job (`run_queue`) plus a broader multi-ISO queue job (`run_queue_all`); coverage across all 7 ISOs for queue data is not yet uniform.
