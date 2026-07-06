"""Carbon intensity (lbs CO2/MWh) across all seven ISOs via the managed API."""

from kardashev import Client

kl = Client()

latest = kl.carbon_latest()
print(latest)
