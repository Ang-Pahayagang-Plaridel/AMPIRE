from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import logging
import time

from .gauth import get_sheets_service
from AMPIRE.utils.utils import is_rate_limit_error
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

@retry(
    retry=retry_if_exception(is_rate_limit_error),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    before=lambda retry_state: logger.warning(
        f"Attempt {retry_state.attempt_number} to batch update values due to rate limit"
    )
)
def batch_update_values(spreadsheet_id, updates):
    """
    Update multiple ranges in a Google Sheet in a single batch request.
    
    :param spreadsheet_id: The ID of the spreadsheet to update.
    :param updates: A list of tuples, each containing (range_name, values).
    """
    service = get_sheets_service()
    
    # Prepare the request body
    data = []
    for range_name, values in updates:
        data.append({
            'range': range_name,
            'values': values
        })
    
    body = {
        'data': data,
        'valueInputOption': 'RAW'
    }
    
    try:
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        logger.info(f"Updated {result.get('totalUpdatedCells')} cells.")
    except HttpError as error:
        logger.error(f"Failed to batch update values: {error}")
        if error.resp.status in [403, 429]:  # Handle quota errors
            logger.warning("Quota exceeded. Retrying failed updates...")
            # Implement retry logic for failed updates
            retry_failed_updates(service, spreadsheet_id, updates)
        raise

def retry_failed_updates(service, spreadsheet_id, updates):
    """
    Retry the failed updates after a quota error.
    
    :param service: The Google Sheets service instance.
    :param spreadsheet_id: The ID of the spreadsheet to update.
    :param updates: A list of tuples, each containing (range_name, values).
    """
    for range_name, values in updates:
        for attempt in range(5):  # Retry up to 5 times
            try:
                body = {
                    'values': values
                }
                result = service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                logger.info(f"Successfully updated range {range_name}: {result.get('updatedCells')} cells.")
                break  # Exit the retry loop on success
            except HttpError as error:
                logger.error(f"Failed to update range {range_name}: {error}")
                if attempt < 4:  # Don't wait on the last attempt
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached for range {range_name}.")

@retry(
    retry=retry_if_exception(is_rate_limit_error),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    before=lambda retry_state: logger.warning(
        f"Attempt {retry_state.attempt_number} to batch read values due to rate limit"
    )
)
def batch_read_values(spreadsheet_id, ranges):
    """
    Read multiple ranges from a Google Sheet in a single batch request.
    
    :param spreadsheet_id: The ID of the spreadsheet to read from.
    :param ranges: A list of A1 notation ranges to read.
    :return: A dictionary with ranges as keys and their corresponding values.
    """
    service = get_sheets_service()
    
    # Prepare the request body
    body = {
        'ranges': ranges,
        'majorDimension': 'ROWS'  # or 'COLUMNS' depending on your needs
    }
    
    try:
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Extract values from the result
        values = {range_name: result.get('valueRanges', {}).get(range_name, {}).get('values', []) for range_name in ranges}
        logger.info(f"Successfully read values for ranges: {', '.join(ranges)}")
        return values
    except HttpError as error:
        logger.error(f"Failed to batch read values: {error}")
        raise

