from __future__ import annotations

import uvicorn

from .config import settings


def run() -> None:
    uvicorn.run(
        "services.realtime.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
