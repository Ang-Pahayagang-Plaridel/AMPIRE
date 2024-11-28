from django.shortcuts import render
from django.http import JsonResponse
from googleapiclient.errors import HttpError
import time

from . import drive

from AMPIRE.utils import handle_error, batch_callback, logger
# Create your views here.

# def compute_sirk_process(issue_folder_id, ):

def create_folders_process(issue_name, sections, online_sirk, parent_folder_id):
    service = drive.get_drive_service()
    batch_size = 50  # Limit the batch size
    online_sirk_folder_id = drive.get_folder_id("01. ONLINE SIRK", parent_folder_id)
    online_sirk_folders = drive.get_folders(online_sirk_folder_id)

    if online_sirk_folders is None or len(online_sirk_folders) == 0 : bilang = 1
    else : bilang = max(int(online_sirk_folder['name'].split('.')[0]) for online_sirk_folder in online_sirk_folders) + 1
    
    main_folder = drive.create_folder(service, f"{bilang:02d}. {issue_name.upper()}", online_sirk_folder_id)

    if not main_folder:
        logger.error(f"Failed to create the main folder: {issue_name}")
        return None
    main_folder_id = main_folder.get('id')
    
    for section in sections:
        section_folder = drive.create_folder(service, section['name'], main_folder_id)
        if not section_folder:
            logger.error(f"Failed to create section folder: {section['name']}")
            continue
        section_folder_id = section_folder.get('id')
        
        for sirk in online_sirk:
            sirk_folder = drive.create_folder(service, sirk, section_folder_id)
            if not sirk_folder:
                logger.error(f"Failed to create online sirk folder: {sirk}")
                continue
            sirk_folder_id = sirk_folder.get('id')
            
            members = section['members']
            for i in range(0, len(members), batch_size):
                batch = service.new_batch_http_request(callback=batch_callback)
                for member in members[i:i + batch_size]:
                    batch.add(service.files().create(body={
                        'name': member,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [sirk_folder_id]
                    }, fields='id'))
                batch.execute()
                logger.info(f"Executed batch for members {i} to {i + batch_size}")
                time.sleep(1)  # Add delay to prevent hitting limits

    return main_folder_id

def create_APP_folder_process(app_folder_name):
    service = drive.get_drive_service()
    app_folder = drive.create_folder(service, app_folder_name, drive.AMPIRE_FOLDER_ID)
    app_folder_id = app_folder.get('id')
    sirk_folder = drive.create_folder(service, "SIRKULASYON", app_folder_id)
    sirk_folder_id = sirk_folder.get('id')
    sirk_template_file_id = "1T1-MMOp7HHfKVzDN6KbJR0DVBKBkzJpBnPqa2MeTz9M"
    sirk_file_id = drive.copy_file(service, sirk_template_file_id, "ONLINE SIRK TRACKER")
    drive.move_file(service, sirk_file_id, sirk_folder_id)
    drive.create_folder(service, "01. ONLINE SIRK", sirk_folder_id)
    drive.create_folder(service, "02. MANUAL SIRK", sirk_folder_id)
    
    return app_folder_id