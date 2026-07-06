# Changelog

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
