"""Token verifier for API key authentication.

Implements the MCP SDK's TokenVerifier protocol for API key validation.
The TokenVerifier protocol is also the extension point for custom auth
(e.g. JWT/OAuth2) in managed deployments.
"""
from __future__ import annotations

from mcp.server.auth.provider import AccessToken, TokenVerifier


class ApiKeyVerifier:
    """Validates bearer tokens against a set of static API keys."""

    def __init__(self, valid_keys: set[str]) -> None:
        self._valid_keys = valid_keys

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or token not in self._valid_keys:
            return None
        return AccessToken(token=token, client_id="api_key_client", scopes=["all"])


def create_verifier(config) -> ApiKeyVerifier | None:
    """Create the appropriate token verifier based on config.auth_mode."""
    if config.auth_mode == "api_key":
        return ApiKeyVerifier(valid_keys=config.valid_api_keys)
    return None
