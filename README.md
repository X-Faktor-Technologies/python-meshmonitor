# MeshMonitor API Client

An asynchronous, typed Python client for MeshMonitor 4.14.x–4.15.x and Home
Assistant.

Version 0.8.0 is a pre-1.0 source release candidate. No package has been
published to PyPI yet. Until an owner-approved package release is recorded,
install a reviewed source checkout with the development workflow below. The
reserved distribution name is `meshmonitor-api-client`.

The import package is `meshmonitor_client`.

## Safety boundary

The client exposes no generic request method. Its radio-write surface is limited
to explicit message methods and four source-scoped Meshtastic node requests.
It has no administration, discovery, configuration, or remote telemetry-request
API.

## Supported reads

- Source discovery
- Source status
- Meshtastic nodes
- Channels
- Network summary and typed topology nodes/edges
- Stored, channel-filtered neighbor/SNR links
- Stored traceroutes and bounded node-pair route history
- Bounded node telemetry and link-quality history
- Paginated position history with private-position denials preserved
- Global read-only automation metadata and bounded per-automation run history
- Current coordinator telemetry
- Reticulum bridge status, public identity, interfaces, announced
  destinations, bounded LXMF conversations/messages, and stored paths
- Bounded source-scoped Meshtastic and MeshCore stored-message history plus the
  compatibility unified-feed read, with stable identities and reception metadata
- Capability probing
- Coordinator-oriented source snapshots with mandatory status/node data and
  serialized best-effort network, topology, stored-neighbor, and telemetry
  reads

## Supported writes

- One unsplit Meshtastic channel or direct message (maximum 200 UTF-8 bytes)
- One MeshCore channel message (maximum 130 bytes) or direct message (maximum
  150 bytes)
- One MeshCore flood advert for an explicitly selected source
- Meshtastic traceroute, position, NodeInfo, and NeighborInfo requests through
  MeshMonitor's authenticated v1 action routes
- Meshtastic server-only favorite and ignored-state metadata changes with
  device synchronization explicitly disabled, plus MeshCore server-only
  favorites

MeshCore contacts are supported through MeshMonitor's protocol-specific
`/api/sources/{id}/meshcore` read routes because MeshMonitor does not normalize
them through the canonical v1 node endpoint. Reticulum data uses the corresponding
`/api/sources/{id}/reticulum` routes and deliberately excludes radio
configuration, path probes, remote status queries, identity writes, and LXMF
sending. Stored Meshtastic history uses the
canonical per-source v1 message route; stored MeshCore history uses its verified
source-scoped route. The compatibility unified method remains available for
session-capable deployments, but MeshMonitor 4.14.1 does not bind Bearer tokens
on that optional-auth route. Active
Discovery, remote telemetry requests, reactions, and every other radio write
remain excluded.

Source and node history methods are scoped to their explicit identifiers.
Automation definitions are global in MeshMonitor, require `automations:read`,
and expose only typed metadata plus bounded per-definition run reads; serialized
configuration, trigger, state, and log content is deliberately not modeled.
All history methods enforce MeshMonitor 4.14.x's verified limits. HTTP 403
remains a permission error, HTTP 404 remains an unsupported/missing-resource
error, and a successful empty collection is returned as supported-but-empty
data. Malformed typed collections fail closed as response errors rather than
being presented as honest empty history or topology.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/python -m pip install build
.venv/bin/python -m build
```

Live contract checks are opt-in and require `MESHMONITOR_URL`,
`MESHMONITOR_TOKEN`, and optionally `MESHMONITOR_SOURCE_ID`. Never commit
tokens or raw production responses.

## Compatibility

- Python 3.12, 3.13, and 3.14
- MeshMonitor 4.14.x and 4.15.x live-tested
- Semantic versioning; pre-1.0 minor releases may extend typed models

See [API compatibility](docs/api-compatibility.md), the
[Reticulum contract](docs/reticulum-contract.md),
[contributing](CONTRIBUTING.md), and the [security policy](SECURITY.md) before
filing an issue.
