"""Opt-in checks against a real MeshMonitor server.

These tests record no response bodies and are skipped unless explicitly enabled.
"""

from __future__ import annotations

import os

import pytest

from meshmonitor_client import MeshMonitorClient


@pytest.mark.asyncio
async def test_live_read_contract() -> None:
    url = os.getenv("MESHMONITOR_URL")
    token = os.getenv("MESHMONITOR_TOKEN")
    if not url or not token:
        pytest.skip("live MeshMonitor environment is not configured")

    async with MeshMonitorClient(url, token, timeout=15) as client:
        sources = await client.get_sources()
        assert sources
        requested_source = os.getenv("MESHMONITOR_SOURCE_ID")
        source = next((item for item in sources if item.id == requested_source), sources[0])
        capabilities = await client.probe_capabilities(source.id)
        assert capabilities.sources
        assert capabilities.status
        assert capabilities.nodes
        nodes = await client.get_nodes(source.id)
        assert nodes, "node list is empty; verify channel View on map permission"
        messages = await client.get_unified_messages(limit=5)
        assert isinstance(messages, list)
