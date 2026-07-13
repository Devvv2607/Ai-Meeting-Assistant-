"""Frontend origin policy — one source of truth for CORS and OAuth redirects.

vercel.app subdomains are handed out first-come-first-served, so a bare
prefix match ("ai-meeting-assistant*") could be claimed by anyone. The regex
therefore requires the team-scoped suffix (only this Vercel team can mint
those), and the stable production alias is allowed exactly.
"""

import os
import re

# Deployment + branch aliases of this project, e.g.
# ai-meeting-assistant-<hash>-devmittal2607-3043s-projects.vercel.app
VERCEL_TEAM_ORIGIN_REGEX = (
    r"^https://ai-meeting-assistant[a-z0-9-]*"
    r"-devmittal2607-3043s-projects\.vercel\.app$"
)

_STATIC_ORIGINS = [
    "http://localhost:3000",   # Local development (original port)
    "http://localhost:3001",   # Local development (alternate port)
    "http://localhost:3002",   # Local development (alternate port)
    "http://127.0.0.1:3000",   # Alternative localhost
    "http://127.0.0.1:3001",   # Alternative localhost (alternate port)
    "http://127.0.0.1:3002",   # Alternative localhost (alternate port)
    "http://frontend:3000",    # Docker frontend service
    "https://ai-meeting-assistant-flame.vercel.app",  # Vercel production alias
]


def allowed_origins() -> list:
    """Static allowlist plus comma-separated ALLOWED_ORIGINS from the env."""
    extra = [
        origin.strip().rstrip("/")
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return _STATIC_ORIGINS + extra


def origin_allowed(origin: str) -> bool:
    return origin in allowed_origins() or bool(
        re.match(VERCEL_TEAM_ORIGIN_REGEX, origin)
    )
