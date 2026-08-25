from qdrant_client import QdrantClient
from functools import lru_cache
from app.core.config import get_settings

COLLECTION_NAME = "viora_shorts"
VECTOR_DIM = 20


@lru_cache
def get_qdrant() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)