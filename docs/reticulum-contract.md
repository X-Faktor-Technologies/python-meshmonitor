# Reticulum read contract

MeshMonitor 4.15.1 exposes read-only Reticulum data below
`/api/sources/{source_id}/reticulum`. The client supports `status`, `identity`,
`interfaces`, `destinations`, `messages`, per-peer message history, and `paths`.

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
- Radio configuration, sending, favorites, and identity import/export are out
  of scope for this read-only contract.

The deterministic fixture at `tests/fixtures/reticulum_contract.json` is
synthetic and contains no live identities, addresses, coordinates, or message
content.
