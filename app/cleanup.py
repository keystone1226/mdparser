from __future__ import annotations

import asyncio
import logging

from .config import settings
from .storage import cleanup_expired

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 30 * 60


async def periodic_cleanup() -> None:
    if settings.retention_hours <= 0:
        return
    while True:
        try:
            removed = cleanup_expired()
            if removed:
                logger.info("Cleaned up %d expired conversion(s).", removed)
        except Exception as exc:
            logger.exception("Cleanup task failed: %s", exc)
        await asyncio.sleep(_INTERVAL_SECONDS)
