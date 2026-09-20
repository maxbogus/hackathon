"""Transit-AI backend (FastAPI app).

Architecture: см. `.clinerules/02-architecture.md`.
- `app.main` — FastAPI app factory
- `app.config` — Settings через pydantic-settings
- `app.api.*` — HTTP routers (health, predictions, ...)
- `app.forecast.*` — ML artifact loader
- `app.models.*` — SQLAlchemy 2.0 async models
- `app.schemas.*` — Pydantic request/response schemas
"""

__version__ = "0.1.0"
