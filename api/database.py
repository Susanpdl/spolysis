from __future__ import annotations
from supabase import create_client, Client
from api.config import settings


def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_service_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


service_client: Client = get_service_client()
