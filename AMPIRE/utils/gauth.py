from decouple import config
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from google.auth.exceptions import TransportError, RefreshError
from threading import Lock
from typing import Dict, Any
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
import json
import base64

# Configure logger
logger = logging.getLogger(__name__)

# Define scopes
SCOPES = {
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "drive": ["https://www.googleapis.com/auth/drive"],
}

# Thread-safe cache with lock
_service_cache: Dict[str, Any] = {}
_cache_lock = Lock()

@lru_cache(maxsize=5)  # Cache up to 5 different scope sets
def _load_credentials(scopes: tuple) -> Credentials:
    """Load and cache credentials for reuse."""
    try:
        return Credentials.from_service_account_info(
            json.loads(base64.b64decode(config("GOOGLE_CREDENTIALS_BASE64"))), 
            scopes=scopes)
    except Exception as e:
        logger.exception("Failed to load credentials")
        raise

@retry(
    retry=retry_if_exception_type((HttpError, TransportError, RefreshError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before=lambda retry_state: logger.warning(
        f"Attempt {retry_state.attempt_number} to create service"
    )
)
def get_google_service(api_name: str, api_version: str, scopes: list) -> Any:
    """Lazy initialization of Google API service with auto-refresh support and error handling."""
    cache_key = f"{api_name}_{api_version}"
    
    with _cache_lock:
        if cache_key in _service_cache:
            logger.debug(f"Returning cached service for {api_name}")
            return _service_cache[cache_key]

        try:
            logger.info(f"Creating new service for {api_name}")
            creds = _load_credentials(tuple(scopes))

            if creds.expired:
                try:
                    logger.debug("Refreshing expired credentials")
                    request = Request(timeout=30)
                    creds.refresh(request)
                except (TransportError, RefreshError) as e:
                    logger.warning(f"Failed to refresh credentials: {str(e)}")
                    raise RuntimeError("Google credentials could not be refreshed") from e

            service = build(api_name, api_version, credentials=creds, cache_discovery=False)
            _service_cache[cache_key] = service
            logger.info(f"Successfully created service for {api_name}")
            return service

        except (HttpError, TransportError, RefreshError) as e:
            logger.error(f"Google API error for {api_name}: {str(e)}")
            return None  # Allows graceful handling
        except Exception:
            logger.exception(f"Unexpected error creating {api_name} service")
            raise

def get_sheets_service() -> Any:
    """Return an authenticated Google Sheets API service."""
    return get_google_service("sheets", "v4", SCOPES["sheets"])

def get_drive_service() -> Any:
    """Return an authenticated Google Drive API service."""
    return get_google_service("drive", "v3", SCOPES["drive"])
