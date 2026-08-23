from __future__ import annotations

import pytest

from meshmonitor_client import __version__
from meshmonitor_client.models import (
    AutomationDefinition,
    AutomationRun,
    Channel,
    NeighborLink,
    Node,
    PositionHistoryPage,
    ServerHealth,
    Source,
    TelemetryPoint,
    Topology,
    Traceroute,
    VersionCheck,
)


def test_installed_distribution_exposes_version() -> None:
    assert __version__ == "0.8.0"


def test_source_requires_stable_id() -> None:
    with pytest.raises(ValueError, match="no id"):
        Source.from_dict({"name": "broken"})


def test_server_models_keep_failures_honest() -> None:
    with pytest.raises(ValueError, match="server health"):
        ServerHealth.from_dict({"status": "ok"})
    failure = VersionCheck.from_dict(
        {"updateAvailable": False, "error": "Unable to check for updates"}
    )
    assert failure.update_available is False
    assert failure.current_version is None
    assert failure.error == "Unable to check for updates"


def test_node_requires_stable_id() -> None:
    with pytest.raises(ValueError, match="stable id"):
        Node.from_dict({"longName": "broken"})


def test_automation_models_require_stable_identity_and_status() -> None:
    with pytest.raises(ValueError, match="automation definition"):
        AutomationDefinition.from_dict({"name": "broken"})
    with pytest.raises(ValueError, match="automation run"):
        AutomationRun.from_dict({"id": "run-1", "automationId": "automation-1"})


def test_invalid_numeric_values_become_none() -> None:
    node = Node.from_dict(
        {
            "nodeId": "node",
            "position": {"latitude": "not-a-number", "longitude": None},
            "deviceMetrics": {"batteryLevel": True},
        }
    )
    assert node.latitude is None
    assert node.longitude is None
    assert node.battery_level is None


def test_channel_uses_verified_numeric_id_as_meshtastic_slot() -> None:
    channel = Channel.from_dict({"id": 0, "name": "", "displayName": "Primary", "role": "PRIMARY"})

    assert channel.index == 0
    assert channel.display_name == "Primary"


def test_live_node_shape_uses_top_level_metrics_and_position() -> None:
    node = Node.from_dict(
        {
            "nodeId": "!1234",
            "latitude": 36.1,
            "longitude": -115.2,
            "batteryLevel": 92,
            "voltage": 4.18,
            "channelUtilization": 8.5,
            "airUtilTx": 1.75,
            "hopsAway": 3,
        }
    )

    assert node.latitude == 36.1
    assert node.longitude == -115.2
    assert node.battery_level == 92
    assert node.voltage == 4.18
    assert node.channel_utilization == 8.5
    assert node.air_util_tx == 1.75
    assert node.hops_away == 3


def test_meshcore_contact_requires_public_key() -> None:
    with pytest.raises(ValueError, match="public key"):
        Node.from_meshcore_dict({"name": "broken"})


def test_meshcore_uptime_like_last_heard_is_not_exposed_as_timestamp() -> None:
    node = Node.from_meshcore_dict(
        {"publicKey": "contact", "name": "Contact", "lastHeard": 464_409_000}
    )
    assert node.last_heard is None


def test_topology_parses_typed_nodes_edges_and_unknown_fields() -> None:
    topology = Topology.from_dict(
        {
            "nodes": [
                {
                    "nodeId": "!00000001",
                    "nodeNum": 1,
                    "longName": "Alpha",
                    "latitude": 35.1,
                    "futureNodeField": "retained",
                }
            ],
            "edges": [
                {
                    "from": "!00000001",
                    "to": "!00000002",
                    "route": [3, "!00000004"],
                    "snr": [-7.5, 2],
                    "futureEdgeField": True,
                }
            ],
            "futureTopologyField": {"retained": True},
        }
    )

    assert topology.nodes[0].node_num == 1
    assert topology.nodes[0].raw["futureNodeField"] == "retained"
    assert topology.edges[0].route == (3, "!00000004")
    assert topology.edges[0].snr == (-7.5, 2.0)
    assert topology.raw["futureTopologyField"] == {"retained": True}


def test_traceroute_decodes_database_json_arrays_without_losing_raw() -> None:
    traceroute = Traceroute.from_dict(
        {
            "id": 9,
            "fromNodeNum": 1,
            "toNodeNum": 2,
            "route": "[3,4]",
            "routeBack": "[5]",
            "snrTowards": "[-7.25,2]",
            "snrBack": "not-json",
            "futureField": "retained",
        }
    )

    assert traceroute.id == "9"
    assert traceroute.route == (3, 4)
    assert traceroute.route_back == (5,)
    assert traceroute.snr_towards == (-7.25, 2.0)
    assert traceroute.snr_back == ()
    assert traceroute.raw["futureField"] == "retained"


def test_neighbor_and_telemetry_optional_values_are_typed() -> None:
    neighbor = NeighborLink.from_dict(
        {
            "nodeNum": 1,
            "neighborNodeNum": 2,
            "snr": "7.5",
            "reverseSnr": -3,
            "bidirectional": True,
            "transportClass": "rf",
        }
    )
    point = TelemetryPoint.from_dict(
        {
            "nodeId": "!00000001",
            "telemetryType": "latitude",
            "value": 35.25,
            "rxSnr": -4.5,
            "hopStart": 3,
            "hopLimit": 1,
        }
    )

    assert neighbor.snr == 7.5
    assert neighbor.reverse_snr == -3.0
    assert neighbor.bidirectional is True
    assert point.rx_snr == -4.5
    assert point.hop_start == 3
    assert point.hop_limit == 1


def test_position_history_page_preserves_pagination_and_fix_fields() -> None:
    page = PositionHistoryPage.from_dict(
        {
            "count": 1,
            "total": 8,
            "offset": 2,
            "limit": 1,
            "data": [
                {
                    "timestamp": 1_770_000_000_000,
                    "latitude": 35.25,
                    "longitude": -80.75,
                    "groundSpeed": 4.5,
                    "packetId": 123,
                    "futureFixField": "retained",
                }
            ],
        }
    )

    assert (page.count, page.total, page.offset, page.limit) == (1, 8, 2, 1)
    assert page.fixes[0].longitude == -80.75
    assert page.fixes[0].ground_speed == 4.5
    assert page.fixes[0].raw["futureFixField"] == "retained"
