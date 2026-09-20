"""
Supabase client instances.

- `supabase_anon`  : used only to validate an incoming user's access token
                     (auth.get_user). Safe to use the anon key for this.
- `supabase_admin` : uses the SECRET service_role key. Bypasses RLS and can
                     manage auth users directly (create/update/ban). Only
                     ever used server-side, never exposed to the frontend.
"""
from supabase import create_client, Client

from .config import settings

supabase_anon: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

supabase_admin: Client = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)
