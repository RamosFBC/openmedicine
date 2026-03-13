from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def require_api_key(valid_keys: set[str]):
    async def _check(
        credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    ):
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing API key")
        if credentials.credentials not in valid_keys:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return credentials.credentials

    return Depends(_check)
