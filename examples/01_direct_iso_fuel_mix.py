"""Direct ISO access - no API key required.

Pulls live fuel mix (generation by fuel type) straight from each ISO's
public feed, no Kardashev Labs API involved.
"""

from kardashev import CAISO, ERCOT

caiso = CAISO()
print(caiso.get_fuel_mix().tail())

ercot = ERCOT()
print(ercot.get_fuel_mix().tail())
