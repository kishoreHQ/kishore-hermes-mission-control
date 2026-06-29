"""Session auth middleware stub — extend for Tailscale/OIDC in production."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Single-user personal OS: pass-through in dev; gate in production
        return await call_next(request)
