from __future__ import annotations

from typing import Any

import pytest

from meshmonitor_client import (
    MeshMonitorAuthenticationError,
    MeshMonitorClient,
    MeshMonitorConnectionError,
    MeshMonitorNotFoundError,
    MeshMonitorPermissionError,
    MeshMonitorRateLimitError,
    MeshMonitorResponseError,
    MeshMonitorServerError,
    MeshMonitorTransmitDisabledError,
)

from .conftest import FakeSession, InvalidJson


@pytest.mark.asyncio
async def test_sources_are_typed_and_unknown_fields_retained(
    source_payload: dict[str, Any],
) -> None:
    session = FakeSession({"/api/v1/sources": (200, source_payload)})
    client = MeshMonitorClient("http://mesh.test/", "secret", session=session)  # type: ignore[arg-type]

    sources = await client.get_sources()

    assert sources[0].id == "source-1"
    assert sources[0].type == "meshtastic_tcp"
    assert sources[0].raw["futureField"] == "retained"
    assert session.requests[0][1]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_server_health_and_cached_version_check_are_typed() -> None:
    session = FakeSession(
        {
            "/api/health": (
                200,
                {
                    "status": "ok",
                    "version": "4.14.1",
                    "uptime": 3_600_000,
                    "databaseType": "sqlite",
                    "future": "retained",
                },
            ),
            "/api/version/check": (
                200,
                {
                    "updateAvailable": True,
                    "currentVersion": "4.14.1",
                    "latestVersion": "4.14.2",
                    "releaseUrl": "https://github.com/Yeraze/meshmonitor/releases/tag/v4.14.2",
                    "imageReady": True,
                },
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    health = await client.get_server_health()
    version = await client.get_version_check()

    assert health.version == "4.14.1"
    assert health.uptime_ms == 3_600_000
    assert health.raw["future"] == "retained"
    assert version.update_available is True
    assert version.latest_version == "4.14.2"
    assert [request[0] for request in session.requests] == [
        "http://mesh.test/api/health",
        "http://mesh.test/api/version/check",
    ]


@pytest.mark.asyncio
async def test_nodes_parse_stable_fields(node_payload: dict[str, Any]) -> None:
    session = FakeSession({"/api/v1/sources/source-1/nodes": (200, node_payload)})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    nodes = await client.get_nodes("source-1")

    assert nodes[0].id == "123456"
    assert nodes[0].long_name == "Synthetic Node"
    assert nodes[0].battery_level == 87.0
    assert nodes[0].altitude == 425.5
    assert nodes[0].raw["unknownFutureField"] == {"works": True}


@pytest.mark.asyncio
async def test_source_id_is_escaped() -> None:
    session = FakeSession({"/api/v1/sources/a%2Fb/status": (200, {"ok": True})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    assert (await client.get_status("a/b")).raw == {"ok": True}


@pytest.mark.asyncio
async def test_meshtastic_status_enriches_missing_local_identity() -> None:
    session = FakeSession(
        {
            "/api/v1/sources/source-1/status": (
                200,
                {"data": {"connected": True}},
            ),
            "/api/status?sourceId=source-1": (
                200,
                {
                    "connection": {
                        "localNode": {
                            "nodeId": "!1234abcd",
                            "longName": "Local Node",
                            "shortName": "LOCAL",
                        }
                    }
                },
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    status = await client.get_status("source-1")

    assert status.connected is True
    assert status.local_node_id == "!1234abcd"
    assert status.long_name == "Local Node"
    assert status.short_name == "LOCAL"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, MeshMonitorAuthenticationError),
        (403, MeshMonitorPermissionError),
        (404, MeshMonitorNotFoundError),
        (503, MeshMonitorServerError),
    ],
)
async def test_http_errors_are_specific(status: int, error: type[Exception]) -> None:
    session = FakeSession({"/api/v1/sources": (status, {"error": "nope"})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(error):
        await client.get_sources()


@pytest.mark.asyncio
async def test_invalid_json_is_rejected() -> None:
    session = FakeSession({"/api/v1/sources": (200, InvalidJson())})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(MeshMonitorResponseError, match="invalid JSON"):
        await client.get_sources()


@pytest.mark.asyncio
async def test_closed_shared_session_is_reported_as_connection_error() -> None:
    class ClosedSession:
        def get(self, *_: Any, **__: Any) -> None:
            raise RuntimeError("Session is closed")

    client = MeshMonitorClient(
        "http://mesh.test",
        "secret",
        session=ClosedSession(),  # type: ignore[arg-type]
    )

    with pytest.raises(MeshMonitorConnectionError):
        await client.get_sources()


@pytest.mark.asyncio
async def test_malformed_list_is_rejected() -> None:
    session = FakeSession({"/api/v1/sources": (200, {"sources": ["not-an-object"]})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(MeshMonitorResponseError, match="non-object"):
        await client.get_sources()


@pytest.mark.asyncio
async def test_capabilities_flag_silent_node_filtering() -> None:
    base = "/api/v1/sources/source-1"
    session = FakeSession(
        {
            f"{base}/status": (200, {"connected": True}),
            f"{base}/nodes": (200, {"nodes": []}),
            f"{base}/channels": (200, {"channels": []}),
            f"{base}/network": (200, {}),
            f"{base}/network/topology": (403, {"error": "denied"}),
            f"{base}/telemetry": (200, {"telemetry": []}),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    capabilities = await client.probe_capabilities("source-1")

    assert capabilities.nodes is True
    assert capabilities.topology is False
    assert capabilities.node_visibility_suspect is True


@pytest.mark.asyncio
async def test_snapshot_collects_coordinator_data(node_payload: dict[str, Any]) -> None:
    base = "/api/v1/sources/source-1"
    session = FakeSession(
        {
            f"{base}/status": (200, {"data": {"connected": True}}),
            "/api/status?sourceId=source-1": (
                200,
                {"connection": {"localNode": {"nodeId": "!1234abcd"}}},
            ),
            f"{base}/nodes": (200, node_payload),
            f"{base}/network": (200, {"data": {"totalNodes": 58, "activeNodes": 12}}),
            f"{base}/network/topology": (
                200,
                {
                    "data": {
                        "nodes": [{"nodeId": "!0001", "longName": "Topology Node"}],
                        "edges": [],
                    }
                },
            ),
            "/api/sources/source-1/neighbor-info": (
                200,
                {
                    "data": [
                        {
                            "nodeId": "!0001",
                            "neighborNodeId": "!0002",
                            "snr": 7.5,
                        }
                    ]
                },
            ),
            f"{base}/telemetry": (
                200,
                {
                    "data": [
                        {
                            "id": "record-1",
                            "nodeId": "123456",
                            "telemetryType": "battery",
                            "value": 87,
                            "unit": "%",
                            "timestamp": 1770000000,
                        }
                    ]
                },
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_snapshot("source-1")

    assert snapshot.status.connected is True
    assert snapshot.nodes[0].voltage == 4.12
    assert snapshot.network is not None
    assert snapshot.network.total_nodes == 58
    assert snapshot.topology is not None
    assert snapshot.topology.nodes[0].long_name == "Topology Node"
    assert snapshot.topology.edges == ()
    assert snapshot.neighbors[0].snr == 7.5
    assert snapshot.telemetry[0].telemetry_type == "battery"
    assert snapshot.errors == {}
    assert [request[0] for request in session.requests] == [
        f"http://mesh.test{base}/status",
        "http://mesh.test/api/status?sourceId=source-1",
        f"http://mesh.test{base}/nodes",
        f"http://mesh.test{base}/network",
        f"http://mesh.test{base}/network/topology",
        "http://mesh.test/api/sources/source-1/neighbor-info",
        f"http://mesh.test{base}/telemetry",
        f"http://mesh.test{base}/channels",
    ]


@pytest.mark.asyncio
async def test_snapshot_retains_mandatory_data_when_optional_endpoint_fails(
    node_payload: dict[str, Any],
) -> None:
    base = "/api/v1/sources/source-1"
    session = FakeSession(
        {
            f"{base}/status": (200, {"data": {"connected": True}}),
            f"{base}/nodes": (200, node_payload),
            f"{base}/network": (503, {"error": "unavailable"}),
            f"{base}/network/topology": (404, {"error": "unsupported"}),
            "/api/sources/source-1/neighbor-info": (403, {"error": "denied"}),
            f"{base}/telemetry": (403, {"error": "denied"}),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_snapshot("source-1")

    assert len(snapshot.nodes) == 1
    assert snapshot.network is None
    assert snapshot.topology is None
    assert snapshot.neighbors == ()
    assert snapshot.telemetry == ()
    assert set(snapshot.errors) == {"neighbors", "network", "telemetry", "topology"}
    assert snapshot.errors["topology"].startswith("resource not found:")
    assert snapshot.errors["neighbors"].startswith("permission denied for")


@pytest.mark.asyncio
async def test_snapshot_preserves_supported_empty_intelligence_data(
    node_payload: dict[str, Any],
) -> None:
    base = "/api/v1/sources/source-1"
    session = FakeSession(
        {
            f"{base}/status": (200, {"data": {"connected": True}}),
            f"{base}/nodes": (200, node_payload),
            f"{base}/network/topology": (200, {"data": {"nodes": [], "edges": []}}),
            "/api/sources/source-1/neighbor-info": (200, {"data": []}),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_snapshot("source-1")

    assert snapshot.topology is not None
    assert snapshot.topology.nodes == ()
    assert snapshot.topology.edges == ()
    assert snapshot.neighbors == ()
    assert "topology" not in snapshot.errors
    assert "neighbors" not in snapshot.errors


@pytest.mark.asyncio
async def test_snapshot_fails_when_nodes_are_unavailable() -> None:
    base = "/api/v1/sources/source-1"
    session = FakeSession(
        {
            f"{base}/status": (200, {"data": {"connected": True}}),
            f"{base}/nodes": (503, {"error": "unavailable"}),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(MeshMonitorServerError):
        await client.get_snapshot("source-1")


@pytest.mark.asyncio
async def test_meshcore_snapshot_uses_protocol_specific_read_routes() -> None:
    base = "/api/sources/meshcore-1/meshcore"
    session = FakeSession(
        {
            f"{base}/info": (
                200,
                {
                    "data": {
                        "connected": True,
                        "identity": {"publicKey": "local-key", "name": "Local"},
                    }
                },
            ),
            f"{base}/nodes": (
                200,
                {
                    "data": [
                        {
                            "publicKey": "contact-key",
                            "name": "Synthetic Contact",
                            "lastHeard": 1_770_000_000_000,
                            "latitude": 35.0,
                            "longitude": -115.0,
                            "batteryMv": 4120,
                            "model": "Synthetic MeshCore",
                            "ver": "1.2.3",
                        }
                    ]
                },
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_meshcore_snapshot("meshcore-1")

    assert snapshot.status.connected is True
    assert snapshot.nodes[0].id == "contact-key"
    assert snapshot.nodes[0].last_heard == 1_770_000_000
    assert snapshot.nodes[0].voltage == 4.12
    assert snapshot.network is None
    assert snapshot.telemetry == ()
    assert [request[0] for request in session.requests] == [
        "http://mesh.test/api/sources/meshcore-1/meshcore/info",
        "http://mesh.test/api/sources/meshcore-1/meshcore/nodes",
        "http://mesh.test/api/v1/sources/meshcore-1/channels",
    ]


@pytest.mark.asyncio
async def test_unified_messages_normalize_both_protocols() -> None:
    payload = [
        {
            "dedupKey": "123:p456",
            "fromNodeId": "!0000007b",
            "fromNodeLongName": "Synthetic Meshtastic",
            "toNodeId": "^all",
            "channel": 0,
            "channelName": "LongFast",
            "text": "hello",
            "timestamp": 1_770_000_000_000,
            "createdAt": 1_770_000_000_100,
            "receptions": [
                {
                    "sourceId": "meshtastic-1",
                    "sourceName": "Mesh A",
                    "sourceType": "meshtastic_tcp",
                    "rxSnr": 7.5,
                    "rxRssi": -92,
                }
            ],
        },
        {
            "dedupKey": "mc:meshcore-1:9",
            "fromNodeId": "public-key",
            "fromNodeLongName": "Synthetic MeshCore",
            "toNodeId": "channel-0",
            "channel": 0,
            "channelName": "Public",
            "text": "world",
            "timestamp": 1_770_000_001_000,
            "createdAt": 1_770_000_001_100,
            "receptions": [
                {
                    "sourceId": "meshcore-1",
                    "sourceName": "Mesh B",
                    "sourceType": "meshcore",
                    "rxSnr": 4,
                    "rxRssi": -101,
                }
            ],
        },
    ]
    session = FakeSession({"/api/unified/messages?limit=100": (200, payload)})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    messages = await client.get_unified_messages()

    assert [message.protocol for message in messages] == ["meshtastic", "meshcore"]
    assert messages[0].id == "123:p456"
    assert messages[1].from_name == "Synthetic MeshCore"
    assert messages[1].receptions[0].rssi == -101


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "path"),
    [
        ("traceroute", "traceroute"),
        ("position", "request-position"),
        ("nodeinfo", "request-nodeinfo"),
        ("neighbors", "request-neighbors"),
    ],
)
async def test_meshtastic_node_actions_use_source_scoped_v1_routes(action: str, path: str) -> None:
    route = f"/api/v1/sources/source-1/actions/{path}"
    session = FakeSession({route: (200, {"success": True, "data": {"requestId": 7}})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.request_meshtastic_node_action("source-1", "!a1b2c3d4", action, channel=2)

    assert result.success is True
    assert result.request_id == 7
    assert session.requests[-1][0] == f"http://mesh.test{route}"
    assert session.posts[-1] == (
        f"http://mesh.test{route}",
        {"destination": "!a1b2c3d4", "channel": 2},
    )


@pytest.mark.asyncio
async def test_meshtastic_node_action_rejects_unknown_action_and_bad_destination() -> None:
    client = MeshMonitorClient("http://mesh.test", "secret", session=FakeSession({}))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsupported"):
        await client.request_meshtastic_node_action("source-1", "!a1b2c3d4", "telemetry")
    with pytest.raises(ValueError, match="node_id"):
        await client.request_meshtastic_node_action("source-1", "bad", "position")


@pytest.mark.asyncio
async def test_unified_messages_escape_query_and_validate_limit() -> None:
    session = FakeSession(
        {"/api/unified/messages?limit=25&before=1234&channel=Ops+%26+Alerts": (200, [])}
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    assert await client.get_unified_messages(limit=25, before=1234, channel="Ops & Alerts") == []
    with pytest.raises(ValueError, match="limit"):
        await client.get_unified_messages(limit=501)


@pytest.mark.asyncio
async def test_meshtastic_source_history_parses_verified_v1_envelope() -> None:
    messages = [
        {
            "id": f"source-1_42_{1000 + index}",
            "fromNodeNum": 42,
            "fromNodeId": "!0000002a",
            "toNodeId": "^all",
            "text": f"synthetic-{index}",
            "channel": 0,
            "timestamp": 1_770_000_000_000 + index,
            "rxTime": 1_770_000_000_000 + index,
            "rxSnr": 7.5,
            "rxRssi": -98,
            "createdAt": 1_770_000_000_100 + index,
        }
        for index in range(7)
    ]
    path = "/api/v1/sources/source-1/messages?limit=200"
    session = FakeSession({path: (200, {"success": True, "count": 7, "data": messages})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.get_meshtastic_messages(
        "source-1", source_name="Synthetic source", limit=200
    )

    assert len(result) == 7
    assert result[0].id == "mt:!0000002a:p1000"
    assert result[0].channel == 0
    assert result[0].protocol == "meshtastic"
    assert result[0].receptions[0].source_id == "source-1"
    assert result[0].receptions[0].source_name == "Synthetic source"


@pytest.mark.asyncio
async def test_meshtastic_source_history_empty_and_cross_source_dedup_id() -> None:
    shared = {
        "id": "receiver_42_123456",
        "fromNodeNum": 42,
        "fromNodeId": "!0000002a",
        "text": "synthetic",
        "channel": 0,
        "timestamp": 1_770_000_000_000,
        "createdAt": 1_770_000_000_100,
    }
    session = FakeSession(
        {
            "/api/v1/sources/source-a/messages?limit=25": (200, {"data": [shared]}),
            "/api/v1/sources/source-b/messages?limit=25": (
                200,
                {"data": [{**shared, "id": "other_42_123456"}]},
            ),
            "/api/v1/sources/empty/messages?limit=25": (
                200,
                {"success": True, "count": 0, "data": []},
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    first = await client.get_meshtastic_messages("source-a", limit=25)
    second = await client.get_meshtastic_messages("source-b", limit=25)

    assert first[0].id == second[0].id == "mt:!0000002a:p123456"
    assert await client.get_meshtastic_messages("empty", limit=25) == []


@pytest.mark.asyncio
async def test_meshcore_source_history_preserves_protocol_and_channel() -> None:
    path = "/api/sources/meshcore-1/meshcore/messages?limit=200"
    payload = {
        "success": True,
        "count": 1,
        "data": [
            {
                "id": "stored-9",
                "fromPublicKey": "channel-0",
                "fromName": "Synthetic sender",
                "toPublicKey": "local-key",
                "text": "synthetic",
                "timestamp": 1_770_000_000_000,
                "createdAt": 1_770_000_000_100,
                "rssi": -101,
                "snr": 4,
            }
        ],
    }
    session = FakeSession({path: (200, payload)})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.get_meshcore_messages(
        "meshcore-1", source_name="Synthetic MeshCore", limit=200
    )

    assert result[0].id == "mc:meshcore-1:stored-9"
    assert result[0].protocol == "meshcore"
    assert result[0].channel == 0
    assert result[0].from_name == "Synthetic sender"
    assert result[0].receptions[0].rssi == -101


@pytest.mark.asyncio
async def test_source_message_limits_are_bounded() -> None:
    client = MeshMonitorClient("http://mesh.test", "secret", session=FakeSession({}))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="limit"):
        await client.get_meshtastic_messages("source-1", limit=501)
    with pytest.raises(ValueError, match="limit"):
        await client.get_meshcore_messages("source-1", limit=0)


@pytest.mark.asyncio
async def test_meshtastic_ignore_is_server_only_and_source_scoped() -> None:
    path = "/api/nodes/%211234abcd/ignored"
    session = FakeSession({path: (200, {"success": True})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    await client.set_meshtastic_ignored("source-1", "!1234abcd", True)

    assert session.posts == [
        (
            "http://mesh.test" + path,
            {"sourceId": "source-1", "isIgnored": True, "syncToDevice": False},
        )
    ]


@pytest.mark.asyncio
async def test_meshtastic_node_delete_is_decimal_source_scoped_and_typed() -> None:
    path = "/api/nodes/305441741?sourceId=source-1"
    session = FakeSession(
        {
            path: (
                200,
                {
                    "nodeNum": 305441741,
                    "nodeName": "Retired node",
                    "messagesDeleted": 3,
                    "traceroutesDeleted": 2,
                    "telemetryDeleted": 9,
                },
            )
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.delete_meshtastic_node("source-1", "!1234abcd")

    assert result.node_num == 305441741
    assert result.node_name == "Retired node"
    assert result.messages_deleted == 3
    assert result.traceroutes_deleted == 2
    assert result.telemetry_deleted == 9
    assert session.deletes == [f"http://mesh.test{path}"]


@pytest.mark.asyncio
async def test_meshtastic_node_delete_rejects_ambiguous_identifiers() -> None:
    client = MeshMonitorClient("http://mesh.test", "secret", session=FakeSession({}))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="8 hexadecimal"):
        await client.delete_meshtastic_node("source-1", "1234")


@pytest.mark.asyncio
async def test_extended_reads_are_typed_and_narrowly_routed() -> None:
    session = FakeSession(
        {
            "/api/v1/sources/source-1/network/topology": (
                200,
                {
                    "success": True,
                    "data": {
                        "nodes": [{"nodeId": "!00000001", "nodeNum": 1}],
                        "edges": [
                            {
                                "from": "!00000001",
                                "to": "!00000002",
                                "route": [3],
                                "snr": [-7.5],
                            }
                        ],
                    },
                },
            ),
            "/api/sources/source-1/neighbor-info": (
                200,
                [
                    {
                        "nodeNum": 1,
                        "neighborNodeNum": 2,
                        "nodeId": "!00000001",
                        "neighborNodeId": "!00000002",
                        "snr": 6.5,
                        "bidirectional": True,
                    }
                ],
            ),
            "/api/v1/sources/source-1/traceroutes?limit=25": (
                200,
                {
                    "success": True,
                    "data": [
                        {
                            "id": 4,
                            "fromNodeNum": 1,
                            "toNodeNum": 2,
                            "route": "[3]",
                            "snrTowards": "[-5.5]",
                        }
                    ],
                },
            ),
            "/api/traceroutes/history/1/2?sourceId=source-1&limit=1000": (
                200,
                [{"id": 5, "fromNodeNum": 2, "toNodeNum": 1, "route": "[]"}],
            ),
            "/api/telemetry/%2100000001?sourceId=source-1&hours=0.25": (
                200,
                [
                    {
                        "nodeId": "!00000001",
                        "nodeNum": 1,
                        "telemetryType": "voltage",
                        "timestamp": 1_770_000_000_000,
                        "value": 4.12,
                    }
                ],
            ),
            "/api/telemetry/%2100000001/linkquality?sourceId=source-1&hours=168": (
                200,
                {
                    "success": True,
                    "data": [{"timestamp": 1_770_000_000_000, "quality": 84.5}],
                },
            ),
            (
                "/api/v1/sources/source-1/nodes/%2100000001/position-history"
                "?limit=10000&offset=2&since=100&before=200"
            ): (
                200,
                {
                    "success": True,
                    "count": 1,
                    "total": 3,
                    "offset": 2,
                    "limit": 10000,
                    "data": [
                        {
                            "timestamp": 150,
                            "latitude": 35.0,
                            "longitude": -80.0,
                            "packetId": 7,
                        }
                    ],
                },
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    topology = await client.get_topology("source-1")
    neighbors = await client.get_neighbors("source-1")
    traceroutes = await client.get_traceroutes("source-1", limit=25)
    history = await client.get_route_history("source-1", 1, 2, limit=5000)
    telemetry = await client.get_node_telemetry_history("source-1", "!00000001", hours=0.25)
    link_quality = await client.get_node_link_quality("source-1", "!00000001", hours=500)
    positions = await client.get_position_history(
        "source-1",
        "!00000001",
        since=100,
        before=200,
        limit=20_000,
        offset=2,
    )

    assert topology.edges[0].snr == (-7.5,)
    assert neighbors[0].bidirectional is True
    assert traceroutes[0].route == (3,)
    assert history[0].from_node_num == 2
    assert telemetry[0].value == 4.12
    assert link_quality[0].quality == 84.5
    assert positions.fixes[0].packet_id == 7


async def _call_extended_endpoint(client: MeshMonitorClient, endpoint: str) -> Any:
    if endpoint == "topology":
        return await client.get_topology("source-1")
    if endpoint == "neighbors":
        return await client.get_neighbors("source-1")
    if endpoint == "traceroutes":
        return await client.get_traceroutes("source-1", limit=25)
    if endpoint == "route_history":
        return await client.get_route_history("source-1", 1, 2, limit=50)
    if endpoint == "telemetry":
        return await client.get_node_telemetry_history("source-1", "node-1", hours=24)
    if endpoint == "link_quality":
        return await client.get_node_link_quality("source-1", "node-1", hours=24)
    if endpoint == "position_history":
        return await client.get_position_history("source-1", "node-1")
    raise AssertionError(f"unknown extended endpoint {endpoint}")


_EXTENDED_ENDPOINT_CASES = [
    (
        "topology",
        "/api/v1/sources/source-1/network/topology",
        {"data": {"nodes": [], "edges": []}},
    ),
    ("neighbors", "/api/sources/source-1/neighbor-info", {"data": []}),
    (
        "traceroutes",
        "/api/v1/sources/source-1/traceroutes?limit=25",
        {"data": []},
    ),
    (
        "route_history",
        "/api/traceroutes/history/1/2?sourceId=source-1&limit=50",
        {"data": []},
    ),
    (
        "telemetry",
        "/api/telemetry/node-1?sourceId=source-1&hours=24",
        {"data": []},
    ),
    (
        "link_quality",
        "/api/telemetry/node-1/linkquality?sourceId=source-1&hours=24",
        {"data": []},
    ),
    (
        "position_history",
        "/api/v1/sources/source-1/nodes/node-1/position-history?limit=1000&offset=0",
        {"count": 0, "total": 0, "offset": 0, "limit": 1000, "data": []},
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("endpoint", "path", "payload"), _EXTENDED_ENDPOINT_CASES)
async def test_extended_endpoints_preserve_supported_empty(
    endpoint: str, path: str, payload: Any
) -> None:
    session = FakeSession({path: (200, payload)})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await _call_extended_endpoint(client, endpoint)

    if endpoint == "topology":
        assert result.nodes == ()
        assert result.edges == ()
    elif endpoint == "position_history":
        assert result.fixes == ()
        assert result.total == 0
    else:
        assert result == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("endpoint", "path", "payload"), _EXTENDED_ENDPOINT_CASES)
@pytest.mark.parametrize(
    ("status", "error"), [(403, MeshMonitorPermissionError), (404, MeshMonitorNotFoundError)]
)
async def test_extended_permission_and_unsupported_states_remain_errors(
    endpoint: str,
    path: str,
    payload: Any,
    status: int,
    error: type[Exception],
) -> None:
    del payload
    session = FakeSession({path: (status, {"error": "not available"})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(error):
        await _call_extended_endpoint(client, endpoint)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "path", "payload"),
    [
        (
            "topology",
            "/api/v1/sources/source-1/network/topology",
            {"data": {"nodes": "not-a-list", "edges": []}},
        ),
        ("neighbors", "/api/sources/source-1/neighbor-info", {"data": "not-a-list"}),
        (
            "traceroutes",
            "/api/v1/sources/source-1/traceroutes?limit=25",
            {"data": ["not-an-object"]},
        ),
        (
            "route_history",
            "/api/traceroutes/history/1/2?sourceId=source-1&limit=50",
            {"data": "not-a-list"},
        ),
        (
            "telemetry",
            "/api/telemetry/node-1?sourceId=source-1&hours=24",
            {"data": "not-a-list"},
        ),
        (
            "link_quality",
            "/api/telemetry/node-1/linkquality?sourceId=source-1&hours=24",
            {"data": "not-a-list"},
        ),
        (
            "position_history",
            "/api/v1/sources/source-1/nodes/node-1/position-history?limit=1000&offset=0",
            {"data": "not-a-list"},
        ),
    ],
)
async def test_extended_malformed_collections_are_not_empty_results(
    endpoint: str, path: str, payload: Any
) -> None:
    session = FakeSession({path: (200, payload)})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(MeshMonitorResponseError):
        await _call_extended_endpoint(client, endpoint)


@pytest.mark.asyncio
async def test_extended_bounds_are_validated_before_requests() -> None:
    session = FakeSession({})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="limit"):
        await client.get_traceroutes("source-1", limit=201)
    with pytest.raises(ValueError, match="from_node_num"):
        await client.get_route_history("source-1", -1, 2)
    with pytest.raises(ValueError, match="hours"):
        await client.get_node_telemetry_history("source-1", "node", hours=0.1)
    with pytest.raises(ValueError, match="offset"):
        await client.get_position_history("source-1", "node", offset=-1)

    assert session.requests == []


@pytest.mark.asyncio
async def test_extended_clamped_bounds_are_present_in_exact_routes() -> None:
    session = FakeSession(
        {
            "/api/traceroutes/history/1/2?sourceId=source-1&limit=1": (200, []),
            "/api/telemetry/node-1/linkquality?sourceId=source-1&hours=168": (200, []),
            ("/api/v1/sources/source-1/nodes/node-1/position-history?limit=1&offset=0"): (
                200,
                {"data": []},
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    assert await client.get_route_history("source-1", 1, 2, limit=-10) == []
    assert await client.get_node_link_quality("source-1", "node-1", hours=500) == []
    assert (await client.get_position_history("source-1", "node-1", limit=0)).fixes == ()

    assert [request[0] for request in session.requests] == [
        "http://mesh.test/api/traceroutes/history/1/2?sourceId=source-1&limit=1",
        "http://mesh.test/api/telemetry/node-1/linkquality?sourceId=source-1&hours=168",
        ("http://mesh.test/api/v1/sources/source-1/nodes/node-1/position-history?limit=1&offset=0"),
    ]


@pytest.mark.asyncio
async def test_automation_reads_are_typed_bounded_and_narrowly_routed() -> None:
    session = FakeSession(
        {
            "/api/automations": (
                200,
                [
                    {
                        "id": "automation-1",
                        "name": "Synthetic daily check",
                        "description": "Fixture only",
                        "enabled": True,
                        "config": '{"sensitive":true}',
                        "createdByUserId": 4,
                        "createdAt": 1_770_000_000_000,
                        "updatedAt": 1_770_000_001_000,
                        "futureField": "retained",
                    }
                ],
            ),
            "/api/automations/automation-1/runs?limit=20": (
                200,
                [
                    {
                        "id": "run-1",
                        "automationId": "automation-1",
                        "sourceId": "source-1",
                        "status": "completed",
                        "state": '{"private":true}',
                        "triggerEvent": '{"text":"not projected"}',
                        "log": "[]",
                        "startedAt": 1_770_000_002_000,
                        "updatedAt": 1_770_000_003_000,
                    }
                ],
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    definitions = await client.get_automations()
    runs = await client.get_automation_runs("automation-1")

    assert definitions[0].id == "automation-1"
    assert definitions[0].enabled is True
    assert definitions[0].created_by_user_id == 4
    assert definitions[0].raw["futureField"] == "retained"
    assert runs[0].id == "run-1"
    assert runs[0].automation_id == "automation-1"
    assert runs[0].status == "completed"
    assert not hasattr(runs[0], "state")
    assert [request[0] for request in session.requests] == [
        "http://mesh.test/api/automations",
        "http://mesh.test/api/automations/automation-1/runs?limit=20",
    ]


@pytest.mark.asyncio
async def test_automation_reads_preserve_supported_empty_collections() -> None:
    session = FakeSession(
        {
            "/api/automations": (200, []),
            "/api/automations/automation-1/runs?limit=5": (200, []),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    assert await client.get_automations() == []
    assert await client.get_automation_runs("automation-1", limit=5) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [(403, MeshMonitorPermissionError), (404, MeshMonitorNotFoundError)],
)
async def test_automation_permission_and_unsupported_states_remain_errors(
    status: int, error: type[Exception]
) -> None:
    session = FakeSession({"/api/automations": (status, {"error": "not available"})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(error):
        await client.get_automations()


@pytest.mark.asyncio
async def test_malformed_automation_responses_are_rejected() -> None:
    session = FakeSession(
        {
            "/api/automations": (200, {"data": {"id": "not-a-list"}}),
            "/api/automations/automation-1/runs?limit=20": (
                200,
                [{"id": "run-1", "automationId": "automation-1"}],
            ),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(MeshMonitorResponseError, match="JSON array"):
        await client.get_automations()
    with pytest.raises(MeshMonitorResponseError, match="malformed automation run"):
        await client.get_automation_runs("automation-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 201, True, 1.5])
async def test_automation_request_bounds_are_validated_before_requests(
    limit: Any,
) -> None:
    session = FakeSession({})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="limit"):
        await client.get_automation_runs("automation-1", limit=limit)
    with pytest.raises(ValueError, match="automation_id"):
        await client.get_automation_runs("   ")

    assert session.requests == []


def test_empty_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="token"):
        MeshMonitorClient("http://mesh.test", "  ")


@pytest.mark.asyncio
async def test_meshtastic_send_is_explicit_bounded_and_typed() -> None:
    path = "/api/v1/sources/source-1/messages"
    session = FakeSession(
        {
            path: (
                201,
                {
                    "success": True,
                    "data": {
                        "messageId": "123_456",
                        "requestId": 456,
                        "deliveryState": "pending",
                        "messageCount": 1,
                    },
                },
            )
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.send_meshtastic_message("source-1", " test ", channel=0)

    assert result.message_id == "123_456"
    assert result.delivery_state == "pending"
    assert session.posts == [("http://mesh.test" + path, {"text": " test ", "channel": 0})]


@pytest.mark.asyncio
async def test_meshtastic_direct_send_can_preserve_reply_linkage() -> None:
    path = "/api/v1/sources/source-1/messages"
    session = FakeSession({path: (201, {"success": True})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    await client.send_meshtastic_message(
        "source-1", "reply", to_node_id="!1234abcd", reply_id=3726281140
    )

    assert session.posts == [
        (
            "http://mesh.test" + path,
            {"text": "reply", "toNodeId": "!1234abcd", "replyId": 3726281140},
        )
    ]


@pytest.mark.asyncio
async def test_meshcore_send_enforces_destination_and_utf8_limit() -> None:
    path = "/api/sources/meshcore-1/meshcore/messages/send"
    session = FakeSession({path: (200, {"success": True, "message": "Message sent"})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]
    key = "ab" * 32

    result = await client.send_meshcore_message("meshcore-1", "hello", to_public_key=key)

    assert result.success is True
    assert session.posts[0][1] == {"text": "hello", "toPublicKey": key}
    with pytest.raises(ValueError, match="150"):
        await client.send_meshcore_message("meshcore-1", "é" * 76, to_public_key=key)


@pytest.mark.asyncio
async def test_meshcore_advert_requires_positive_acceptance() -> None:
    path = "/api/sources/meshcore-1/meshcore/advert"
    session = FakeSession({path: (200, {"success": True})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    await client.send_meshcore_advert("meshcore-1")

    assert session.posts == [("http://mesh.test" + path, {})]

    rejected = FakeSession({path: (200, {"success": False})})
    rejected_client = MeshMonitorClient(  # type: ignore[arg-type]
        "http://mesh.test", "secret", session=rejected
    )
    with pytest.raises(MeshMonitorResponseError, match="did not accept"):
        await rejected_client.send_meshcore_advert("meshcore-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (403, MeshMonitorPermissionError),
        (409, MeshMonitorTransmitDisabledError),
        (429, MeshMonitorRateLimitError),
    ],
)
async def test_send_errors_are_specific(status: int, error: type[Exception]) -> None:
    path = "/api/v1/sources/source-1/messages"
    session = FakeSession({path: (status, {"error": "denied"})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(error):
        await client.send_meshtastic_message("source-1", "test", channel=0)


def test_client_exposes_no_generic_write_methods() -> None:
    public = {name for name in dir(MeshMonitorClient) if not name.startswith("_")}
    assert not public.intersection({"post", "put", "patch", "delete", "request", "send"})
