# API compatibility contract

## Verified baseline

- MeshMonitor 4.14.x and 4.15.1
- Canonical source-scoped routes under `/api/v1/sources/{sourceId}`
- Bearer-token authentication
- Meshtastic and MeshCore node/contact modeling plus read-only Reticulum data

## Compatibility rules

1. Unknown object fields are retained in each model's `raw` mapping.
2. Missing required stable identifiers reject the affected object.
3. Optional or malformed scalar metrics degrade to `None`.
4. Authentication, authorization, missing resources, server failures, invalid JSON,
   and transport failures raise distinct exceptions.
5. A successful but empty node list is reported as a possible channel map-visibility
   permission problem during capability probing.
6. Stored topology, neighbor, traceroute, telemetry/link-quality, and position
   history reads are source-scoped and bounded; none initiate a mesh request.
7. HTTP 403, HTTP 404, and successful empty collections remain distinct so a
   consumer cannot mislabel denied or unsupported data as empty.
8. The only writes are the explicit bounded messaging and server-persistent
   favorite methods; the client does not expose a generic HTTP request API.
9. Coordinator snapshots fetch topology and stored neighbors serially with the
   other source reads; optional endpoint failures are keyed in `errors`, while
   successful empty collections remain typed data.
10. Global automation definitions and per-definition runs require
    `automations:read`; run requests are limited to 1–200 records and typed
    models do not project serialized config, trigger, state, or log content.

## Known upstream behavior

- The bundled OpenAPI document does not enumerate the complete mounted API surface.
- Node visibility depends on channel-level **View on map** permission.
- MeshCore contacts are available through a legacy protocol-specific route but are not
  returned by the canonical v1 node endpoint in 4.14.1.
- Requests observed on an ARM64 lab host take roughly 0.54–0.60 seconds, so consumers
  should coordinate and stagger refreshes rather than poll each entity independently.
- Stored topology edges and history collections may legitimately be empty.
- Bearer-token consumers should use the typed per-source Meshtastic and
  MeshCore stored-message reads. MeshMonitor 4.14.1's optional-auth unified
  route does not bind the token user and can return an anonymous empty array.
- Position-history access can additionally require `nodes_private:read`; a
  denial is never converted into an empty trail.
- Automation definitions are global rather than source-scoped, and their run
  history is returned newest-first with a server-enforced maximum of 200.
