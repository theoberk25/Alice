"""Shared get_metrics()/set_fan_speed(value) MCP, backed by ALICE by default.

Streamable HTTP remains :8790/mcp. The file store is explicit standalone test
mode only; the integrated path never writes it or opens a serial device.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
from pathlib import Path
from typing import Annotated

import anyio
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token

from .state import MachineState
from .thermal_state import ThermalState
from services.thermal_demo.client import DemoClient


class AgentTokens:
    """Preprovisioned per-agent bearer identities; never accept a claimed agent ID."""
    def __init__(self, tokens):
        if (not tokens or any(type(t) is not str or not t or not t.isascii()
                              or any(c.isspace() for c in t) for t in tokens.values())
                or len(set(tokens.values())) != len(tokens)):
            raise ValueError('Distinct nonempty ASCII agent tokens required')
        self.tokens = dict(tokens)

    async def verify_token(self, token):
        for agent, expected in self.tokens.items():
            if hmac.compare_digest(token.encode(), expected.encode()):
                return AccessToken(token=token, client_id=agent, scopes=['metrics'])
        return None


def create_server(backends, *, host='127.0.0.1', port=8790, agent_tokens=None):
    if host not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Bind MCP to loopback; use an authenticated SSH tunnel for remote agents')
    options = {}
    if agent_tokens is not None:
        if set(backends) != set(agent_tokens):
            raise ValueError('Backends must match authenticated agent identities')
        authority = f'http://{("[::1]" if host == "::1" else host)}:{port}'
        options.update(token_verifier=AgentTokens(agent_tokens),
                       auth=AuthSettings(issuer_url=authority, resource_server_url=authority+'/mcp',
                                         required_scopes=['metrics']))
    elif set(backends) != {'file'}:
        raise ValueError('Governed backends require authenticated agent tokens')
    mcp = FastMCP('machine-metrics', host=host, port=port, stateless_http=True, **options)

    def backend():
        if agent_tokens is None:
            return backends['file']
        access = get_access_token()
        if access is None or access.client_id not in backends:
            raise ValueError('Authenticated agent required')
        return backends[access.client_id]

    @mcp.tool()
    async def get_metrics() -> dict:
        """Read actual fan_speed (%), server_temperature (F), power_consumption (W).

        Governed mode adds authorized target, run/revision, battery and genuine
        request outcomes. Null metrics mean unconfigured/unavailable, never zero.
        """
        return await anyio.to_thread.run_sync(backend().read)

    @mcp.tool()
    async def set_fan_speed(value: Annotated[float, Field(strict=True, ge=0, le=100)],
                            request_id: str | None = None, run_id: str | None = None,
                            expected_revision: Annotated[int, Field(strict=True, ge=0)] | None = None) -> dict:
        """Propose fan percent, preserving the established single-value call.

        ALICE alone applies changes. HOLD/DENY/UNKNOWN return ok:false; inspect
        decision/application and get_metrics rather than assuming a fan change.
        For retries pass the exact request_id/run_id/expected_revision returned
        earlier. Never mint a new ID to bypass a held or uncertain request.
        """
        target = backend()
        try:
            if isinstance(target, ThermalState):
                return await anyio.to_thread.run_sync(lambda: target.set_fan_speed(
                    value, request_id=request_id, run_id=run_id, expected_revision=expected_revision))
            if any(v is not None for v in (request_id, run_id, expected_revision)):
                raise ValueError('Run-bound requests require the governed backend')
            metrics = await anyio.to_thread.run_sync(lambda: target.set_fan_speed(value))
            return {'ok': True, 'fan_speed': metrics['fan_speed'], 'metrics': metrics,
                    'standalone_test': True, 'governed': False}
        except (ValueError, OSError):
            return {'ok': False, 'error': 'Request refused or backend unavailable; inspect current metrics before retrying'}
    return mcp


def build_server():
    host = os.environ.get('LIGHT_MCP_HOST', '127.0.0.1')
    port = int(os.environ.get('LIGHT_MCP_PORT', '8790'))
    kind = os.environ.get('MACHINE_BACKEND', 'thermal')
    if kind == 'thermal':
        tokens = json.loads(os.environ.get('THERMAL_AGENT_TOKENS', '{}'))
        AgentTokens(tokens)
        url = os.environ.get('THERMAL_DEMO_URL', 'http://127.0.0.1:8795')
        backends = {agent: ThermalState(DemoClient(url, token), agent) for agent, token in tokens.items()}
        return create_server(backends, host=host, port=port, agent_tokens=tokens)
    if kind != 'file':
        raise ValueError('MACHINE_BACKEND must be thermal or file')
    state = MachineState(os.environ.get('MACHINE_STATE_FILE', str(Path(__file__).with_name('machine_state.json'))),
        seeds={'fan_speed': float(os.environ.get('SEED_FAN_SPEED', '50')),
               'server_temperature': float(os.environ.get('SEED_SERVER_TEMPERATURE', '45')),
               'power_consumption': float(os.environ.get('SEED_POWER_CONSUMPTION', '300'))},
        fan_min=float(os.environ.get('FAN_SPEED_MIN', '0')), fan_max=float(os.environ.get('FAN_SPEED_MAX', '100')))
    return create_server({'file': state}, host=host, port=port)


def main():
    logging.basicConfig(level=os.environ.get('LIGHT_MCP_LOG_LEVEL', 'INFO'))
    build_server().run(transport='streamable-http')


if __name__ == '__main__':
    main()
