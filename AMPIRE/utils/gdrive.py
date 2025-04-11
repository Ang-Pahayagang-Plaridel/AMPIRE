from decouple import config
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import logging

# Import is_rate_limit_error from AMPIRE/utils.py
from AMPIRE.utils.utils import is_rate_limit_error
from .gauth import get_drive_service

logger = logging.getLogger(__name__)

# Load shared drive and folder IDs from environment variables
SHARED_DRIVE_ID = config('SHARED_DRIVE_ID')
AMPIRE_FOLDER_ID = config('AMPIRE_FOLDER_ID')
SHARED_DRIVE_ID = "0AHjAxpfHTZNeUk9PVA"
AMPIRE_FOLDER_ID = "1cD4inKGSRsV4NBxsFBqLD3fBhSkK7KRd"

@retry(
    retry=retry_if_exception(is_rate_limit_error),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    before=lambda retry_state: logger.warning(
        f"Attempt {retry_state.attempt_number} to list drive files due to rate limit"
    )
)
def list_drive_files(query=None, max_results=10):
    """
    List files from Google Drive with an optional search query.
    
    :param query: The search query to filter files.
    :param max_results: Maximum number of results to return.
    :return: List of files matching the query.
    """
    service = get_drive_service()
    try:
        results = service.files().list(
            q=query,
            pageSize=max_results,
            fields="files(id, name)"
        ).execute()
        return results.get('files', [])
    except HttpError as error:
        logger.error(f"Google Drive API failed: {error}")
        raise Exception(f"Google Drive API failed: {error}")

@retry(
    retry=retry_if_exception(is_rate_limit_error),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    before=lambda retry_state: logger.warning(
        f"Attempt {retry_state.attempt_number} to get folder ID due to rate limit"
    )
)
def get_folder_id(folder_name, parent_folder_id):
    """
    Retrieve the folder ID from Google Drive using the folder name.
    Searches within the specified parent folder.
    
    :param folder_name: The name of the folder to search for.
    :param parent_folder_id: The ID of the parent folder to search within.
    :return: The ID of the folder if found, otherwise None.
    """
    service = get_drive_service()
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields="files(id, name)",
            corpora='drive',
            driveId=SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        if not files:
            logger.warning(f"No folder found with name: {folder_name}")
            return None
        if len(files) > 1:
            logger.warning(f"Multiple folders found with name: {folder_name}, returning the first one.")
        
        return files[0]['id']
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        raise Exception(f"Failed to retrieve folder ID for {folder_name}: {error}")
