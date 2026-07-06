"""Generator interconnection queue entries across every tracked ISO."""

from kardashev import Client

kl = Client()

queue = kl.queue(iso="ERCOT", status="active")
print(queue.head())
