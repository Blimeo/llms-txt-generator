# apps/worker/worker/database.py
"""Database operations and Supabase client management."""

import os
import logging
from typing import Optional

from supabase import create_client, Client

from .constants import ENV_SUPABASE_URL, ENV_SUPABASE_KEY

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """Get Supabase client using environment variables."""
    url = os.environ.get(ENV_SUPABASE_URL)
    key = os.environ.get(ENV_SUPABASE_KEY)
    
    if not url or not key:
        raise ValueError(f"{ENV_SUPABASE_URL} and {ENV_SUPABASE_KEY} environment variables are required")
    
    return create_client(url, key)
