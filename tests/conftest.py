from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest


class FakeResponse:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def json(self, *, content_type: str | None = None) -> Any:
        del content_type
        if isinstance(self._payload, InvalidJson):
            raise ValueError("invalid JSON")
        return json.loads(json.dumps(self._payload))


class FakeSession:
    def __init__(self, routes: Mapping[str, tuple[int, Any]]) -> None:
        self.routes = routes
        self.requests: list[tuple[str, dict[str, str]]] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.deletes: list[str] = []
        self.closed = False

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append((url, kwargs.get("headers", {})))
        path = "/" + url.split("/", 3)[-1]
        status, payload = self.routes.get(path, (404, {"error": "not found"}))
        return FakeResponse(status, payload)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append((url, kwargs.get("headers", {})))
        self.posts.append((url, kwargs.get("json", {})))
        path = "/" + url.split("/", 3)[-1]
        status, payload = self.routes.get(path, (404, {"error": "not found"}))
        return FakeResponse(status, payload)

    def delete(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append((url, kwargs.get("headers", {})))
        self.deletes.append(url)
        path = "/" + url.split("/", 3)[-1]
        status, payload = self.routes.get(path, (404, {"error": "not found"}))
        return FakeResponse(status, payload)

    async def close(self) -> None:
        self.closed = True


class InvalidJson:
    pass


@pytest.fixture
def source_payload() -> dict[str, Any]:
    return {
        "sources": [
            {
                "id": "source-1",
                "name": "Lab Meshtastic",
                "type": "meshtastic_tcp",
                "enabled": True,
                "futureField": "retained",
            }
        ]
    }


@pytest.fixture
def node_payload() -> dict[str, Any]:
    return {
        "nodes": [
            {
                "nodeId": 123456,
                "longName": "Synthetic Node",
                "shortName": "SYN",
                "lastHeard": 1770000000,
                "position": {"latitude": 35.0, "longitude": -80.0, "altitude": 425.5},
                "deviceMetrics": {"batteryLevel": 87},
                "voltage": 4.12,
                "channelUtilization": 11.5,
                "airUtilTx": 2.25,
                "hopsAway": 2,
                "role": "CLIENT",
                "hwModel": "SYNTHETIC",
                "firmwareVersion": "2.7.0",
                "mobile": False,
                "snr": 7.5,
                "rssi": -92,
                "unknownFutureField": {"works": True},
            }
        ]
    }
