from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from meshmonitor_client import MeshMonitorClient

from .conftest import FakeSession


def _contract() -> dict[str, Any]:
    path = Path(__file__).parent / "fixtures" / "meshmonitor_4_16_1_contract.json"
    return json.loads(path.read_text())


@pytest.mark.asyncio
async def test_meshmonitor_4_16_1_source_status_nodes_and_messages_contract() -> None:
    contract = _contract()
    source_id = contract["sourceId"]
    base = f"/api/v1/sources/{source_id}"
    session = FakeSession(
        {
            "/api/v1/sources": (200, contract["sources"]),
            f"{base}/status": (200, contract["status"]),
            f"{base}/nodes": (200, contract["nodesLater"]),
            f"{base}/messages?limit=25": (200, contract["messages"]),
        }
    )
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    sources = await client.get_sources()
    status = await client.get_status(source_id)
    nodes = await client.get_nodes(source_id)
    messages = await client.get_meshtastic_messages(source_id, limit=25)

    assert contract["version"] == "4.16.1"
    assert sources[0].id == source_id
    assert sources[0].raw["observer"]["published"] == 42
    assert status.connected is True
    assert status.local_node_id == "!1234abcd"
    assert nodes[0].last_heard == 1770000060
    assert nodes[0].raw["futureField"] == "retained"
    assert messages[0].id == "mt:!0001e240:p456"
    assert messages[0].text == "Synthetic 4.16.1 contract message"
    assert messages[0].receptions[0].source_id == source_id


def test_meshmonitor_4_16_1_fixture_records_forward_only_last_heard() -> None:
    contract = _contract()
    initial = contract["nodesInitial"]["nodes"][0]["lastHeard"]
    later = contract["nodesLater"]["nodes"][0]["lastHeard"]

    assert later >= initial
