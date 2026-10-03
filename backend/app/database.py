from typing import Tuple, Optional
from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings

client: Optional[MongoClient] = None
db: Optional[Database] = None


def connect_database() -> Database:
    """
    Establish a production-hardened connection pool to MongoDB Atlas.
    """
    global client, db

    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is missing from environment configuration.")

    try:
        client = MongoClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            retryWrites=True
        )

        # Verify connectivity via admin ping
        client.admin.command("ping")
        db = client[settings.MONGODB_DATABASE]
        return db

    except Exception as exc:
        # Avoid exposing raw connection strings containing credentials in exceptions
        sanitized_msg = "Failed to connect to MongoDB instance. Check network or credentials."
        raise RuntimeError(sanitized_msg) from exc


def get_database() -> Database:
    """
    Retrieve active database instance or initialize connection if required.
    """
    global db
    if db is None:
        return connect_database()
    return db


def check_database_readiness() -> Tuple[bool, str]:
    """
    Safe dependency check for readiness probes without exposing credentials.
    Returns:
        (is_ready: bool, message: str)
    """
    global client
    if client is None:
        try:
            connect_database()
        except Exception:
            return False, "Database client uninitialized"

    try:
        if client:
            client.admin.command("ping")
            return True, "Database responsive"
        return False, "Database client unavailable"
    except Exception:
        return False, "Database ping failed"