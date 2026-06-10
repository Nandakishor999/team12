import logging
import os
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


_client = None


def _get_mongodb_client():
    """Create (or reuse) an async MongoDB client.

    Uses motor (async). We keep a module-level singleton so the app can
    reuse connections efficiently.
    """
    global _client
    if _client is not None:
        return _client

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError as exc:
        raise RuntimeError(
            "motor is not installed. Install backend dependencies before running."
        ) from exc

    uri = os.getenv("MONGODB_URI") or settings.__dict__.get("MONGODB_URI")
    # Note: settings currently doesn't define MONGODB_URI; we support env var directly.
    uri = uri or os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not set. Create a backend/.env (or environment variable) with MONGODB_URI."
        )

    _client = AsyncIOMotorClient(uri)
    logger.info("MongoDB client initialized")
    return _client


def get_db():
    """Return an async database handle.

    Mongo Atlas connection string should include a default database.
    If not, we fall back to 'hrbot'.
    """
    client = _get_mongodb_client()

    # motor/AsyncIOMotorClient exposes get_default_database() when DB is in URI.
    try:
        db = client.get_default_database()
        if db is not None:
            return db
    except Exception:
        pass

    return client["hrbot"]

