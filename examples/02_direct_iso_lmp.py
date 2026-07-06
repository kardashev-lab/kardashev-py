"""Direct ISO LMP (locational marginal price) access - no API key required."""

from kardashev import CAISO, ERCOT, MISO

caiso = CAISO()
print(caiso.get_lmp(market="RT", node="TH_SP15_GEN-APND"))

ercot = ERCOT()
print(ercot.get_lmp(market="DA"))

miso = MISO()
print(miso.get_lmp(market="RT"))
