from supabase import create_client, Client
from functools import lru_cache
from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)