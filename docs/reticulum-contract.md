# Reticulum contract

MeshMonitor 4.15.1 exposes Reticulum data below
`/api/sources/{source_id}/reticulum`. The client supports `status`, `identity`,
`interfaces`, `destinations`, `messages`, per-peer message history, and `paths`.
It also supports one deliberate LXMF write through `POST /messages`.

All observed routes return `{ "success": true, "data": ... }`. Unknown fields
remain available through each model's `raw` mapping. Hashes are public routing
identifiers, never private identity material.

Important semantics:

- A destination is an announced identity retained by MeshMonitor, not a generic
  continuously-online node.
- `identity` returns only the bridge's public LXMF destination hash.
- Conversation summaries contain a latest message and count. Full history is a
  separate bounded per-peer read.
- `state=delivered` describes LXMF delivery state. `method` is independent and
  may be `opportunistic`.
- `signatureValidated` and `ratcheted` are independent security metadata.
- RSSI, SNR, and quality are nullable. LAN/TCP delivery in the verified 4.15.1
  contract returned null and clients must not invent radio metrics.
- Reading `paths` does not perform a path probe. Probe and remote-status routes
  remain deliberately unsupported because they can generate network traffic.
- `send_reticulum_message` accepts one 32-character destination hash and up to
  4,096 UTF-8 bytes. It may include a title, one of MeshMonitor's supported
  delivery methods, and a hexadecimal reply hash. It never retries.
- The send route needs source-scoped `messages:write` and a connected Reticulum
  bridge. MeshMonitor's returned row records the initial LXMF delivery state;
  later state changes arrive through normal message polling.
- Radio configuration, favorites, propagation changes, path probes, remote
  status, automatic announces, and identity import/export remain out of scope.

The deterministic fixture at `tests/fixtures/reticulum_contract.json` is
synthetic and contains no live identities, addresses, coordinates, or message
content.
