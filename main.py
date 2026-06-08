from __future__ import annotations

import uvicorn

from core.app import create_app
from core.config import get_settings

settings = get_settings()
app = create_app(settings)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "local",
    )
