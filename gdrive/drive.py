from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from decouple import config
import time

from AMPIRE.utils import logger
import logging

SCOPES = ['https://www.googleapis.com/auth/drive']
SHARED_DRIVE_ID = config('SHARED_DRIVE_ID')
AMPIRE_FOLDER_ID = config('AMPIRE_FOLDER_ID')

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def get_image_files(folder_id, max_retries=5, backoff_factor=2):
    service = get_drive_service()
    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    retries = 0

    while retries < max_retries:
        try:
            results = service.files().list(
                driveId=SHARED_DRIVE_ID,
                corpora='drive',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                q=query,
                fields="files(id, name, mimeType, modifiedTime, createdTime)"
            ).execute()
            return results.get('files', [])
        except HttpError as error:
            if error.resp.status in [500, 503]:
                # Handle server-side errors with a retry
                wait_time = backoff_factor ** retries
                logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to list image files. Error: {error}")
                break  # Break if it's not a retryable error
    raise Exception(f"Failed to list image files after {max_retries} attempts.")

def get_folders(folder_id):
    service = get_drive_service()
    query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    results = service.files().list(
        driveId=SHARED_DRIVE_ID,
        corpora='drive',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        q=query, 
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])
    return items

def get_folder_id(folder_name, parent_folder_id):
    service = get_drive_service()
    query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(
        driveId=SHARED_DRIVE_ID,
        corpora='drive',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        q=query,
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])
    if not items:
        print(f'No folder found with name "{folder_name}" in parent "{parent_folder_id}"')
        return None
    return items[0]['id']

def create_folder(service, folder_name, parent_folder_id):
    # service = get_drive_service()
    try:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(
            supportsAllDrives=True,
            body=folder_metadata, 
            fields='id'
        ).execute()
        print(f'Created folder: {folder_name} with ID: {folder["id"]}')
        return folder
    except HttpError as error:
        print(f'Failed to create folder: {folder_name}. Error: {error}')
        return None

def copy_file(service, file_id, new_name=None):
    try:
        folder_metadata = {}
        if new_name:
            folder_metadata['name'] = new_name
        new_file = service.files().copy(
            supportsAllDrives=True,
            fileId=file_id,
            body=folder_metadata,
            fields='id'
        ).execute()
        print(f'Copied file ID: {new_file["id"]}')
        return new_file['id']
    except HttpError as error:
        print(f'Failed to copy file. Error: {error}')
        return None
    
def move_file(service, file_id, new_folder_id):
    try:
        # Retrieve the existing parents to remove
        file = service.files().get(
            supportsAllDrives=True,
            fileId=file_id,
            fields='parents'
        ).execute()
        previous_parents = ",".join(file.get('parents'))

        # Move the file to the new folder
        file = service.files().update(
            supportsAllDrives=True,
            fileId=file_id,
            addParents=new_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f'Moved file ID: {file["id"]} to folder ID: {new_folder_id}')
    except HttpError as error:
        print(f'Failed to move file. Error: {error}')

def find_gsheet_in_folder(folder_id, file_name, shared_drive_id=None, max_retries=5, backoff_factor=2):
    service = get_drive_service()
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and "
        f"name = '{file_name}' and trashed = false"
    )
    
    retries = 0
    while retries < max_retries:
        try:
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                corpora="drive" if shared_drive_id else "user",
                driveId=shared_drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            items = results.get('files', [])
            if not items:
                print(f'No Google Sheets file found with name "{file_name}" in folder "{folder_id}".')
                return None
            return items[0]['id']  # Return the first match found
        except HttpError as error:
            if error.resp.status in [500, 503]:
                wait_time = backoff_factor ** retries
                print(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"Failed to find Google Sheets file. Error: {error}")
                break  # Exit if it's not a retryable error
    raise Exception(f"Failed to find Google Sheets file after {max_retries} attempts.")

def add_manager_and_set_permissions(folder_id, user_email, max_retries=5, backoff_factor=2):
    service = get_drive_service()
    retries = 0

    while retries < max_retries:
        try:
            # Add the user as a manager
            permission = {
                'type': 'user',
                'role': 'fileOrganizer',
                'emailAddress': user_email
            }
            service.permissions().create(
                fileId=folder_id,
                body=permission,
                sendNotificationEmail=False,
                fields='id',
                supportsAllDrives=True
            ).execute()

            # Set the folder to be accessible by anyone with the link within the DLSU organization
            permission = {
                'type': 'domain',
                'role': 'fileOrganizer',
                'domain': 'dlsu.edu.ph',
                'allowFileDiscovery': False
            }
            service.permissions().create(
                fileId=folder_id,
                body=permission,
                fields='id',
                supportsAllDrives=True
            ).execute()

            print(f"Permissions successfully set for folder {folder_id}.")
            return

        except HttpError as error:
            if error.resp.status in [500, 503]:
                # Handle server-side errors with a retry
                wait_time = backoff_factor ** retries
                print(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"Failed to set permissions. Error: {error}")
                break  # Break if it's not a retryable error

    raise Exception(f"Failed to set permissions after {max_retries} attempts.")