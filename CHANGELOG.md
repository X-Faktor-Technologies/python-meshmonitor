# Changelog

All notable changes are documented here. This project follows Semantic
Versioning while remaining pre-1.0.

## Unreleased

- Declare MeshMonitor 4.16.1 compatibility and add a deterministic synthetic
  contract fixture for source discovery, status, nodes, source-scoped messages,
  and the upstream forward-only `lastHeard` invariant.
- Synchronize the standalone Reticulum send-result guard with the reviewed
  vendored client so an explicit server rejection cannot be presented as sent.
- Expose MeshMonitor's persisted `hideFromMap` node preference as a typed,
  read-only property while retaining unknown response fields.
- Add a typed, bounded source-scoped LXMF direct-message method for
  MeshMonitor 4.15.1's supported Reticulum message endpoint, including
  delivery method and reply-hash validation with no automatic retries.

## 0.8.0 - 2026-08-22

- Synchronize the standalone package with the integration's reviewed vendored
  implementation, including MeshCore identity reads and adverts, bounded
  radio-write timeouts, Meshtastic local-identity enrichment, altitude parsing,
  exact outbound-body preservation, and local node-delete results.
- Add typed GET-only Reticulum status, public identity, interface,
  destination, LXMF conversation/message, and stored-path contracts plus a
  serialized best-effort snapshot. Radio configuration, probing, and private
  identity material remain excluded.
- Add typed read-only exact-server health and cached update-check methods for
  version, uptime, database type, available release, and explicit check errors.
  These methods expose no update or restart action.

- Add typed, bounded source-scoped Meshtastic and MeshCore stored-message reads
  for Bearer-token consumers, with stable protocol identities and reception
  metadata while retaining the legacy unified-feed method for compatibility.
- Reject malformed nested topology and position-history collections instead of
  degrading them to supported-empty data, with deterministic lifecycle and
  request-bound coverage across every supported extended read.
- Add typed global automation-definition metadata and bounded per-definition
  run-history reads behind MeshMonitor's `automations:read` permission, without
  modeling serialized configuration or execution content.
- Clarify that no PyPI package exists yet and make the documented source-build
  workflow install its required build frontend explicitly.
- Add typed, bounded reads for topology, stored neighbor links, stored
  traceroutes and route history, telemetry/link-quality history, and position
  history.
- Preserve unknown response fields and distinguish permission-denied,
  unsupported, and supported-but-empty results.
- Include topology and stored neighbors in serialized coordinator snapshots at
  the consumer's configured source polling interval.

## 0.7.0

- Add typed favorite state and explicit protocol-specific favorite methods.
- Guarantee Meshtastic favorites remain server-side with `syncToDevice=false`.
- Include permission-filtered channel inventories in coordinator snapshots.

## 0.6.0

- Prepare the package for public GitHub and PyPI publication.
- Document Python 3.14 support and release metadata.
- Add reproducible CI, build validation, trusted PyPI publishing, contribution,
  and security documentation.

## 0.5.0

- Add explicit bounded Meshtastic and MeshCore message-send methods.
- Retain the no-generic-request safety boundary.

## 0.4.0

- Add typed unified cross-protocol message history.

## 0.3.0

- Add the MeshCore protocol-specific read adapter.

## 0.2.0

- Add coordinator-oriented source snapshots and typed live fields.

## 0.1.0

- Initial asynchronous, read-only Meshtastic client.
