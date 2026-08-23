from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from meshmonitor_client import MeshMonitorClient

from .conftest import FakeSession


def _contract() -> dict[str, Any]:
    path = Path(__file__).parent / "fixtures" / "reticulum_contract.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _routes(source_id: str = "synthetic-source") -> dict[str, tuple[int, Any]]:
    contract = _contract()
    base = f"/api/sources/{source_id}/reticulum"
    return {
        f"{base}/status": (200, contract["status"]),
        f"{base}/identity": (200, contract["identity"]),
        f"{base}/interfaces": (200, contract["interfaces"]),
        f"{base}/destinations": (200, contract["destinations"]),
        f"{base}/messages": (200, contract["conversations"]),
        f"{base}/messages/{'2' * 32}?limit=100": (200, contract["messages"]),
        f"{base}/paths": (200, contract["paths"]),
    }


@pytest.mark.asyncio
async def test_reticulum_snapshot_parses_verified_read_contract() -> None:
    session = FakeSession(_routes())
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_reticulum_snapshot("synthetic-source")

    assert snapshot.status.connected is True
    assert snapshot.status.mode == "attach"
    assert snapshot.identity is not None
    assert snapshot.identity.destination_hash == "1" * 32
    assert [interface.name for interface in snapshot.interfaces] == [
        "Synthetic TCP Listener",
        "Synthetic RNode",
    ]
    assert snapshot.interfaces[0].raw["futureInterfaceField"] == "retained"
    assert snapshot.destinations[0].display_name == "Synthetic Peer"
    assert snapshot.destinations[0].rssi is None
    assert snapshot.conversations[0].last_message.signature_validated is True
    assert snapshot.conversations[0].last_message.ratcheted is True
    assert snapshot.paths[0].hops == 1
    assert snapshot.errors == {}
    assert [request[0] for request in session.requests] == [
        "http://mesh.test/api/sources/synthetic-source/reticulum/status",
        "http://mesh.test/api/sources/synthetic-source/reticulum/identity",
        "http://mesh.test/api/sources/synthetic-source/reticulum/interfaces",
        "http://mesh.test/api/sources/synthetic-source/reticulum/destinations",
        "http://mesh.test/api/sources/synthetic-source/reticulum/messages",
        "http://mesh.test/api/sources/synthetic-source/reticulum/paths",
    ]


@pytest.mark.asyncio
async def test_reticulum_message_history_is_bounded_and_typed() -> None:
    session = FakeSession(_routes())
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    messages = await client.get_reticulum_messages("synthetic-source", "2" * 32)

    assert messages[0].content == "Synthetic fixture message"
    assert messages[0].state == "delivered"
    assert messages[0].method == "opportunistic"
    assert messages[0].rssi is None
    assert messages[0].raw["sourceId"] == "synthetic-source"


@pytest.mark.asyncio
async def test_reticulum_message_peer_hash_is_validated_before_request() -> None:
    session = FakeSession({})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="32 hexadecimal"):
        await client.get_reticulum_messages("synthetic-source", "not-a-hash")

    assert session.requests == []


@pytest.mark.asyncio
async def test_reticulum_messages_adapt_to_unified_contract() -> None:
    session = FakeSession(_routes())
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    messages = await client.get_reticulum_unified_messages(
        "synthetic-source", "Synthetic RNS", "2" * 32
    )

    assert messages[0].protocol == "reticulum"
    assert messages[0].id.startswith("rns:synthetic-source:")
    assert messages[0].text == "Synthetic fixture message"
    assert messages[0].receptions[0].rssi is None
    assert messages[0].raw["reticulum"]["signatureValidated"] is True


@pytest.mark.asyncio
async def test_reticulum_message_send_is_source_scoped_bounded_and_typed() -> None:
    path = "/api/sources/synthetic-source/reticulum/messages"
    sent = dict(_contract()["messages"]["data"][0])
    sent.update({"state": "sending", "content": "Hello over LXMF"})
    session = FakeSession({path: (200, {"success": True, "data": sent})})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    result = await client.send_reticulum_message(
        "synthetic-source",
        "Hello over LXMF",
        to_destination_hash="2" * 32,
        method="direct",
        reply_to_hash="a1b2",
    )

    assert result.content == "Hello over LXMF"
    assert result.state == "sending"
    assert session.posts == [
        (
            "http://mesh.test" + path,
            {
                "to": "2" * 32,
                "content": "Hello over LXMF",
                "method": "direct",
                "replyToHash": "a1b2",
            },
        )
    ]


@pytest.mark.asyncio
async def test_reticulum_message_send_rejects_invalid_destination_and_method() -> None:
    session = FakeSession({})
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="32 hexadecimal"):
        await client.send_reticulum_message(
            "synthetic-source", "hello", to_destination_hash="not-a-hash"
        )
    with pytest.raises(ValueError, match="delivery method"):
        await client.send_reticulum_message(
            "synthetic-source",
            "hello",
            to_destination_hash="2" * 32,
            method="unsupported",
        )

    assert session.posts == []


@pytest.mark.asyncio
async def test_reticulum_snapshot_keeps_status_when_optional_route_fails() -> None:
    routes = _routes()
    routes["/api/sources/synthetic-source/reticulum/destinations"] = (
        503,
        {"error": "unavailable"},
    )
    session = FakeSession(routes)
    client = MeshMonitorClient("http://mesh.test", "secret", session=session)  # type: ignore[arg-type]

    snapshot = await client.get_reticulum_snapshot("synthetic-source")

    assert snapshot.status.connected is True
    assert snapshot.destinations == ()
    assert set(snapshot.errors) == {"destinations"}
