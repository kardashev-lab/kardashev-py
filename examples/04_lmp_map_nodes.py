"""All pricing nodes with latest LMP + coordinates, for building a map view."""

from kardashev import Client

kl = Client()

nodes = kl.lmp_map(iso="PJM", market="RT")
print(nodes.head())
